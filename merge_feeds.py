from glob import glob
import feedparser
from feedgen.feed import FeedGenerator

# RSSフィード生成器の初期設定
fg = FeedGenerator()
fg.title('製薬会社RSS統合')
fg.link(href='https://example.com/rss_output/combined.xml', rel='self')
fg.description('複数フィードを統合したマスターRSS')
fg.language('ja')
fg.generator("python-feedgen")
fg.docs("http://www.rssboard.org/rss-specification")

# 各フィードファイルを走査
for xml_file in glob('rss_output/*.xml'):
    if 'combined' in xml_file:
        continue  # 統合先自身を除外

    d = feedparser.parse(xml_file)

    # タイトルから製薬会社名を抽出
    feed_title = d.feed.get("title", "")
    if feed_title.endswith("トピックス"):
        source = feed_title.replace("トピックス", "").strip()
    else:
        source = feed_title.strip() or "出典不明"

    for entry in d.entries:
        fe = fg.add_entry()
        fe.title(f"【{source}】{entry.title}")
        fe.link(href=entry.link)
        fe.description(entry.get("summary", ""))

        # pubDate はそのまま文字列として出力（解析なし）
        pub_str = entry.get("published", "")
        if pub_str:
            fe.pubDate(pub_str)

        # GUID は entry.guid または entry.link を使用
        guid = entry.get("guid") or entry.get("link")
        if guid:
            fe.guid(guid.strip(), permalink=False)

# 出力
fg.rss_file('rss_output/combined.xml')
print("✅ 統合RSS生成完了: rss_output/combined.xml")
