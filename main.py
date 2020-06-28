import os
import requests
from xml.etree.ElementTree import Element, fromstring

import bs4

import pandas as pd


# 環境変数を取得
HATENA_ID = os.environ['HATENA_ID']
BLOG_ID = os.environ['BLOG_ID']
API_KEY = os.environ['API_KEY']
FB_CLIENT_ID = os.environ['FB_CLIENT_ID']
FB_CLIENT_SECRET = os.environ['FB_CLIENT_SECRET']
OUTPUT_FILE_NAME = os.environ['OUTPUT_FILE_NAME']


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
        fb_reaction_count.append(engagement['reaction_count'])
        fb_comment_count.append(engagement['comment_count'])
        fb_share_count.append(engagement['share_count'])
        fb_comment_plugin_count.append(engagement['comment_plugin_count'])
        
        # はてなブックマーク数
        res = requests.get(url=f'https://bookmark.hatenaapis.com/count/entries?url={entity["url"]}')
        hatena = res.json()
        hatena_bookmark.append(hatena[entity["url"]])
        url.append(entity["url"])
        title.append(entity["title"])
        published.append(entity["published"])
        
        # はてなスター数
        res = requests.get(url=f'https://s.hatena.com/entry.json?uri={entity["url"]}')
        hatena = res.json()
        # はてなスターの合計
        hatena_star_total.append(len(hatena['entries'][0]['stars']))
        # はてなスターのUU
        hatena_star_uu.append(len(set([item['name'] for item in hatena['entries'][0]['stars']])))

    df_dict = dict()
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


def main():
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
    result.to_csv(OUTPUT_FILE_NAME, index=False, header=True)
    print(f'output the file to {OUTPUT_FILE_NAME}.')

if __name__ == "__main__":
    main()