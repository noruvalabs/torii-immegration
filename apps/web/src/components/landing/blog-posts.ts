import { BLOG_POST_ORDER, type BlogPostMeta } from "./data";

export type BlogPostContent = {
  title: string;
  excerpt: string;
  body: string[];
};

export type BlogPostCopy = Record<"en" | "ja", BlogPostContent>;

export const BLOG_POSTS: Record<string, BlogPostCopy> = {
  "what-sourced-eligibility-means": {
    en: {
      title: "What “sourced eligibility” actually means",
      excerpt:
        "Every rule Torii shows you links back to the government page it came from. Here's why that's the whole point.",
      body: [
        "Most guided-filing tools summarize a rule and hope it's still accurate. Torii does the opposite: every eligibility check and checklist item is written as a direct reflection of a specific, official government page — and that page is linked right next to the rule.",
        "In practice this means two things. First, if a requirement can't be traced to something an immigration authority actually published, Torii doesn't show it to you — no “common wisdom,” no forum advice dressed up as a rule. Second, when guidance changes, the link is how we know it changed, because someone on the team is watching that exact page, not a summary of it three steps removed.",
        "This is also why Torii is deliberately built jurisdiction by jurisdiction instead of all at once. Sourcing a rule properly takes real work — finding the authoritative page, confirming it's current, writing the check so it matches what's actually published. Doing that shallowly across fifty jurisdictions would mean doing it badly everywhere. We'd rather have two jurisdictions that are genuinely trustworthy than twenty that are approximately right.",
        "None of this makes Torii a substitute for legal advice — sourced rules still can't cover every unusual fact pattern, which is exactly why escalation to a licensed professional exists for the cases that fall outside them. But for the parts of a filing that are genuinely rule-based, sourcing means you're never taking our word for it.",
      ],
    },
    ja: {
      title: "「出典のある資格確認」が実際に意味すること",
      excerpt: "Toriiが表示するすべてのルールは、根拠となる政府の公式ページに紐づいています。その理由をご説明します。",
      body: [
        "多くのガイド型申請ツールは、規則を要約し、それが今も正確であることを期待するだけです。Toriiはその逆を行います。すべての資格確認とチェックリスト項目は、特定の公式政府ページの内容をそのまま反映するように作成され、そのページはルールのすぐ隣にリンクされています。",
        "実際には2つのことを意味します。1つ目は、移民当局が実際に公表した内容にたどれない要件は表示しないということです。「一般的にそう言われている」ことや、フォーラムの助言をルールのように見せかけることはありません。2つ目は、案内内容が変わったときにそれを知る方法が、このリンクそのものだということです。要約の要約ではなく、チームの担当者がその公式ページ自体を実際に確認しています。",
        "これが、Toriiがすべての国・地域を一度にではなく、着実に1つずつ対応させている理由でもあります。ルールに正しく出典をつけるには、実際の作業が必要です——権威あるページを見つけ、それが最新であることを確認し、実際に公表されている内容と一致するように確認項目を作成する。これを50の国・地域で浅く行えば、どこでも質の低いものになってしまいます。私たちは、おおよそ正しい20の国・地域よりも、本当に信頼できる2つの国・地域を選びます。",
        "とはいえ、これによってToriiが法律相談の代わりになるわけではありません。出典のあるルールでも、特殊な事情のすべてをカバーすることはできません。だからこそ、その範囲から外れる申請のために、有資格の専門家へのエスカレーションが用意されています。しかし、ルールに基づく部分については、出典があることで、私たちの言葉をただ信じる必要はありません。",
      ],
    },
  },
  "japan-work-visa-renewal-documents": {
    en: {
      title: "Japan work visa renewals: the documents people forget",
      excerpt:
        "The Certificate of Eligibility gets all the attention. Here are the smaller documents that actually delay renewals.",
      body: [
        "When people think about a Japan work visa renewal, the Certificate of Eligibility and the application form get most of the attention — for good reason, since a category mismatch there can sink a renewal outright. But in practice, the delays we see most often come from smaller, easy-to-forget supporting documents.",
        "A Certificate of Employment is the most common one. It sounds redundant if you already have an employment contract, but immigration reviewers want a current statement from your employer confirming your role, salary, and status — dated recently, not the contract you signed when you were hired. If your HR department is slow to issue one, that alone can push a renewal past your current visa's expiry.",
        "Tax and residence certificates are the second common gap. A certificate of tax payment (nōzei shōmeisho) and sometimes a residence certificate (jūminhyō) are frequently required alongside the main application, and both have to be recent — usually issued within the last three months. People who pulled these documents early in the process, then took weeks to finish everything else, often have to go back and re-request them.",
        "The pattern underneath all of this: a renewal isn't one document, it's a small bundle of documents that all need to be true at the same time. Torii's checklist exists specifically to catch this — every item is tied to why it's required and how current it needs to be, so a slow-to-arrive Certificate of Employment doesn't become a surprise in the last week before your visa expires.",
      ],
    },
    ja: {
      title: "日本の就労ビザ更新：見落とされがちな書類",
      excerpt: "在留資格認定証明書ばかりに注目が集まりますが、実際に更新を遅らせるのはもっと小さな書類です。",
      body: [
        "日本の就労ビザ更新というと、在留資格認定証明書と申請書に注目が集まりがちです。カテゴリーの不一致が更新自体を失敗させかねないという理由からで、それも当然です。しかし実際に私たちがよく目にする遅延の原因は、忘れられがちな小さな添付書類です。",
        "最もよくあるのが在職証明書です。すでに雇用契約書があるなら不要に思えるかもしれませんが、審査担当者は現在の役職・給与・在籍状況を確認できる、最近の日付の証明書を求めています。入社時に交わした契約書ではありません。人事部門の発行が遅れると、それだけで現在のビザの有効期限を過ぎてしまうこともあります。",
        "次によくある抜け漏れが、納税証明書と住民票です。納税証明書と、場合によっては住民票が主たる申請書類と合わせて求められることが多く、いずれも最近のもの——通常は過去3か月以内に発行されたもの——である必要があります。手続きの早い段階でこれらを取得し、他の準備に数週間かかった人は、結局取り直しになることがよくあります。",
        "ここに共通するパターンは、更新とは1つの書類ではなく、すべてが同時に有効でなければならない小さな書類の束だということです。Toriiのチェックリストは、まさにこれを見落とさないために存在します。各項目には、なぜ必要か、どれくらい新しいものである必要があるかが紐づいており、発行に時間のかかる在職証明書が、ビザ期限の直前に思わぬ落とし穴になることを防ぎます。",
      ],
    },
  },
  "when-to-escalate-to-a-lawyer": {
    en: {
      title: "When a checklist isn't enough: knowing when to escalate to a lawyer",
      excerpt:
        "Most filings are genuinely rule-based. A few aren't. Here's how Torii tells the difference — and what happens when it does.",
      body: [
        "A good chunk of visa filings really are mechanical: meet the published criteria, submit the right documents, and the outcome follows the rule. That's the part software can help with directly, and it's most of what a Torii case looks like day to day.",
        "But some facts don't fit cleanly into published criteria. A prior visa denial, a gap in employment history, a criminal record from years ago, an unusual sponsor arrangement — these are exactly the situations where a rule engine applying general criteria can't respons­ibly guess at the outcome, because the real answer depends on judgment a licensed professional is trained to make.",
        "Torii is built to recognize this boundary rather than paper over it. When your answers hit one of these flags, the case doesn't just quietly proceed with a best guess — it surfaces the issue plainly and offers escalation to a licensed immigration professional. Nothing is shared automatically; you write a short note describing the situation, confirm consent, and only then does a reviewer see your case.",
        "The reason this matters isn't just accuracy, it's accountability. Software that confidently answers questions it isn't qualified to answer is worse than software that says “this is outside what I can determine.” If your filing is straightforward, you'll likely never see this flow. If it isn't, you'll be glad it exists.",
      ],
    },
    ja: {
      title: "チェックリストだけでは足りないとき：弁護士へのエスカレーションを見極める",
      excerpt: "ほとんどの申請は本当にルールに基づいています。しかし、そうでない場合もあります。Toriiがその違いをどう見極め、その後どうなるかをご紹介します。",
      body: [
        "ビザ申請の多くは、実際に機械的なものです。公表されている基準を満たし、正しい書類を提出すれば、結果はそのルールに従います。これはソフトウェアが直接サポートできる部分であり、Toriiの申請の多くはこの部分にあたります。",
        "しかし、公表された基準にきれいに当てはまらない事情もあります。過去のビザ不許可歴、雇用歴の空白期間、何年も前の犯罪歴、特殊なスポンサー形態——こうした状況こそ、一般的な基準を適用するルールエンジンが無責任に結果を推測してはならない場面です。本当の答えは、有資格の専門家が訓練を受けて行うべき判断に左右されるからです。",
        "Toriiは、この境界を曖昧にせず、はっきりと認識するように設計されています。回答がこうしたフラグに該当した場合、申請は最良の推測のまま静かに進むのではなく、問題を明確に表示し、有資格の移民専門家へのエスカレーションを提案します。何かが自動的に共有されることはありません。状況を説明する短いメッセージを記入し、同意を確認して初めて、レビュー担当者があなたの申請内容を確認します。",
        "これが重要なのは、正確さのためだけではなく、責任の所在を明確にするためです。判断する資格のない問いに自信満々に答えるソフトウェアは、「これは自分が判断できる範囲を超えている」と言うソフトウェアより劣っています。申請がシンプルであれば、このフローを目にすることはほとんどないでしょう。そうでない場合には、この仕組みがあってよかったと感じるはずです。",
      ],
    },
  },
};

export function getBlogPostMeta(slug: string): BlogPostMeta | undefined {
  return BLOG_POST_ORDER.find((post) => post.slug === slug);
}
