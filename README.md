# 概要
はてなブログに投稿した記事のSNSシェア数を取得し、Google spredsheetに出力する。

# 前提
## 環境変数
はてなブログ APIやfacebook APIのアカウント情報を以下の`.env`に記載する。

```
HATENA_ID=******** # はてなブログ管理アカウントのはてなID
BLOG_ID=******** # ドメイン
API_KEY=******** # はてなブログAPIキー
FB_CLIENT_ID=******** # facebook developerアカウントのAPI ID
FB_CLIENT_SECRET=******** # facebook developerアカウントのAPIシークレット
GCP_CREDENTIAL=********.json # GCP credential
SPREDSHEET_KEY=******** # 出力先spredsheet key

```

## gcloud CLIコマンド実行引数
Cloud Functionsへ関数をデプロイしたり、Cloud Schedulerにジョブを登録するために必要なコマンド引数を`.param`に記載する。

```
FUNCTION_NAME=******** # Cloud Functionsにデプロイする関数名
TOPIC=******** # Pub/Subのトピック名
JOB_NAME=******** # Cloud Schedulerのジョブ名
SCHEDULE=******** # Cloud Schedulerのスケジュール(cron式)
```

## Credentialファイル
使用するサービスアカウントのcredentialファイル(json)を`main.py`と同一ディレクトリに配置する。

## Google spredsheet
出力先のspredsheetにおいて使用するサービスアカウントを編集者とし共有設定しておくこと。

# ローカルでの実行
以下を実行することで`.env`に記載したGoogle spredsheetにはてなブログに投稿した記事のSNSシェア数を出力する。

```bash
docker-compose up
```

# Google Cloud Functionsへ関数のデプロイ
以下を実行することでGoogle Cloud Functionsに関数をデプロイする。

```bash
./scripts/deploy_function.sh
```

# Google Cloud Schedulerへのジョブの登録
以下を実行することでGoogle Cloud Schedulerにジョブを登録する。

```bash
./scripts/create_scheduler.sh
```