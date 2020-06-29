import os
import requests
from xml.etree.ElementTree import Element, fromstring
from datetime import datetime
from pytz import timezone

import bs4

import gspread

import pandas as pd

from oauth2client.service_account import ServiceAccountCredentials 


# 環境変数を取得
HATENA_ID = os.environ['HATENA_ID']
BLOG_ID = os.environ['BLOG_ID']
API_KEY = os.environ['API_KEY']
FB_CLIENT_ID = os.environ['FB_CLIENT_ID']
FB_CLIENT_SECRET = os.environ['FB_CLIENT_SECRET']
# OUTPUT_FILE_NAME = os.environ['OUTPUT_FILE_NAME']
GCP_CREDENTIAL = os.environ['GCP_CREDENTIAL']
SPREDSHEET_KEY = os.environ['SPREDSHEET_KEY']


def get_collection_uri(hatena_id: str, blog_id: str, password: str) -> str:
    """
    コレクションURLを取得する。

    Parameters
    ----------
    hatena_id : str
        はてなブログ管理アカウントのはてなID。
    blog_id : str
        ドメイン。
    password : str
        APIキー。

    Returns
    -------
    collection_uri : str
        コレクションURI。
    
    Notes:
    https://gist.github.com/Cartman0/1413821f5185666bd7f89dbcfa72b947
    """
    service_doc_uri = "https://blog.hatena.ne.jp/{hatena_id:}/{blog_id:}/atom".format(hatena_id=hatena_id, blog_id=blog_id)
    res_service_doc = requests.get(url=service_doc_uri, auth=(hatena_id, password))
    if res_service_doc.ok:
        soup_servicedoc_xml = bs4.BeautifulSoup(res_service_doc.content, features="html.parser")
        collection_uri = soup_servicedoc_xml.collection.get("href")
        return collection_uri

    return False


def get_entity_list(element: Element) -> list:
    """
    投稿記事のURL、タイトル、投稿日を取得する。

    Parameters
    ----------
    element : Element
        xml.etree.ElementTree.Elementクラスのオブジェクト。

    Returns
    -------
    entity_list : list
        各投稿記事についてURL、タイトル、投稿日をkeyとする辞書のリスト。

    Notes
    -----
    https://orangain.hatenablog.com/entry/namespaces-in-xpath
    """
    # 名前空間
    prefix = '{http://www.w3.org/2005/Atom}'
    entity_list = list()
    for entry in element.findall(f'{prefix}entry'):
        entity = dict()
        # 投稿記事(entry)ごとに走査
        for item in entry:
            # URL
            if item.get('rel') == 'alternate':
                entity['url'] = item.get('href')
            # タイトル名
            if item.tag == f'{prefix}title':
                entity['title'] = item.text
            # 出版日
            if item.tag == f'{prefix}published':
                entity['published'] = item.text
        entity_list.append(entity)

    return entity_list


def get_fb_access_token(fb_client_id: str, fb_client_secret: str) -> str:
    """
    facebookのapi access tokenを取得する。

    Parameters
    ----------
    fb_client_id : str
        api id。
    fb_client_secret : str
        api key。

    Returns
    -------
    token : str
        facebook api access token。

    """
    res = requests.get(url=f'https://graph.facebook.com/oauth/access_token?client_id={fb_client_id}&client_secret={fb_client_secret}&grant_type=client_credentials')
    return res.json()['access_token']


def get_sns_reaction(entity_list: list, fb_token: str) -> pd.DataFrame:
    """
    facebookのapi access tokenを取得する。

    Parameters
    ----------
    entity_list : list
        各投稿記事についてURL、タイトル、投稿日をkeyとする辞書のリスト。
    fb_token : str
        facebook api access token。

    Returns
    -------
    token : pd.DataFrame
        投稿記事のSNSリアクション実績。
    
    Notes
    -------
    https://www.secret-base.org/entry/Facebook-share-count

    """
    
    fb_reaction_count = list()
    fb_comment_count = list()
    fb_share_count = list()
    fb_comment_plugin_count = list()
    hatena_bookmark = list()
    hatena_star_total = list()
    hatena_star_uu = list()
    url = list()
    title = list()
    published = list()

    for entity in entity_list:
        # facebookのシェア数
        res = requests.get(url=f'https://graph.facebook.com/?id={entity["url"]}&fields=og_object{{engagement}},engagement&access_token={fb_token}')
        engagement = res.json()['engagement']
        fb_reaction_count.append(str(engagement['reaction_count']))
        fb_comment_count.append(str(engagement['comment_count']))
        fb_share_count.append(str(engagement['share_count']))
        fb_comment_plugin_count.append(str(engagement['comment_plugin_count']))
        
        # はてなブックマーク数
        res = requests.get(url=f'https://bookmark.hatenaapis.com/count/entries?url={entity["url"]}')
        hatena = res.json()
        hatena_bookmark.append(str(hatena[entity["url"]]))
        url.append(entity["url"])
        title.append(entity["title"])
        published.append(entity["published"])
        
        # はてなスター数
        res = requests.get(url=f'https://s.hatena.com/entry.json?uri={entity["url"]}')
        hatena = res.json()
        # はてなスターの合計
        hatena_star_total.append(str(len(hatena['entries'][0]['stars'])))
        # はてなスターのUU
        hatena_star_uu.append(str(len(set([item['name'] for item in hatena['entries'][0]['stars']]))))

    df_dict = dict()
    df_dict['datetime'] = [datetime.now(timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')] * len(entity_list)
    df_dict['title'] = title
    df_dict['url'] = url
    df_dict['published'] = published
    df_dict['fb_reaction_count'] = fb_reaction_count
    df_dict['fb_comment_count'] = fb_comment_count
    df_dict['fb_share_count'] = fb_share_count
    df_dict['fb_comment_plugin_count'] = fb_comment_plugin_count
    df_dict['hatena_bookmark'] = hatena_bookmark
    df_dict['hatena_star_total'] = hatena_star_total
    df_dict['hatena_star_uu'] = hatena_star_uu
    
    return pd.DataFrame(df_dict)


def to_spredsheet(df: pd.DataFrame) -> None:
    """
    コレクションURLを取得する。

    Parameters
    ----------
    df : pd.DataFrame
        spredsheetに格納対象のDataFrame。
    
    Notes:
    https://tanuhack.com/gspread-dataframe
    """

    def _toAlpha(num):
        """
        数字からアルファベットを取得する。(例：26→Z、27→AA、10000→NTP)

        Parameters
        ----------
        num : int
            数字。

        Returns
        -------
        alphabet : str
            数字に対応するアルファベット。
        
        """
        if num<=26:
            return chr(64+num)
        elif num%26==0:
            return toAlpha(num//26-1)+chr(90)
        else:
            return toAlpha(num//26)+chr(64+num%26)
    
    #2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    # クレデンシャル設定
    credentials = ServiceAccountCredentials.from_json_keyfile_name(GCP_CREDENTIAL, scope)
    # OAuth2の資格情報を使用してGoogle APIにログイン
    gc = gspread.authorize(credentials)
    # spredsheetを指定
    worksheet = gc.open_by_key(SPREDSHEET_KEY).sheet1

    start_row = len(worksheet.get_all_values()) + 1
    # DataFrameの列数
    col_lastnum = len(df.columns)
    # DataFrameの行数
    row_lastnum = len(df.index)
    # シートが空の場合はヘッダを付与する
    if start_row == 1:
        cell_list = worksheet.range(f'A{start_row}:'+_toAlpha(col_lastnum)+str(row_lastnum+start_row))
        diff = start_row + 1
    else:
        cell_list = worksheet.range(f'A{start_row}:'+_toAlpha(col_lastnum)+str(row_lastnum+start_row-1))
        diff = start_row
    for cell in cell_list:
        if cell.row == 1:
            val = df.columns[cell.col-1]
        else:
            val = df.iloc[cell.row-diff][cell.col-1]
        cell.value = val
    # spredsheetを更新
    worksheet.update_cells(cell_list)


def main(event, context):
    print('started process.')
    # はてなブログ記事のXMLを取得
    collection_uri = get_collection_uri(hatena_id=HATENA_ID, blog_id=BLOG_ID, password=API_KEY)
    res_collection = requests.get(collection_uri, auth=(HATENA_ID, API_KEY))
    # xmlをパース
    root = fromstring(res_collection.text)
    # 投稿記事のURL、タイトル、投稿日を取得
    entity_list = get_entity_list(root)
    print(f'target files: {entity_list}')
    # facebook api access tokenを取得
    token = get_fb_access_token(fb_client_id=FB_CLIENT_ID, fb_client_secret=FB_CLIENT_SECRET)
    # 投稿記事のSNSリアクション実績取得
    result = get_sns_reaction(entity_list=entity_list, fb_token=token)
    # 結果を出力
    to_spredsheet(result)
    print(f'output to spredsheet: https://docs.google.com/spreadsheets/d/{SPREDSHEET_KEY}')

if __name__ == "__main__":
    main()