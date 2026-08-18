export const dictionary = {
  en: {
    nav: {
      howItWorks: "How it works",
      features: "Features",
      pricing: "Pricing",
      blog: "Blog",
      faq: "FAQ",
      signIn: "Sign in",
      dashboard: "Dashboard",
      startCase: "Start your case",
    },
    hero: {
      eyebrow: "Guided visa & immigration filing",
      titleBefore: "File your visa application ",
      titleAccent: "correctly",
      titleAfter: " — for a fraction of a lawyer's fee.",
      body: "Torii walks you from “which forms do I even need?” to a submission-ready packet: a branching intake, a personalized document checklist, and auto-filled government forms — every step sourced to the official page it came from.",
      ctaPrimary: "Start your case",
      ctaSecondary: "See how it works",
      disclaimerBefore: "Torii is ",
      disclaimerStrong: "not a legal advisor",
      disclaimerAfter:
        " — it helps you prepare your own filing, and routes you to a licensed professional the moment your case needs one.",
    },
    heroDemo: {
      caseId: "JP-WORK-2049",
      locale: "EN locale · Live demo",
      steps: {
        intake: "Intake",
        eligibility: "Eligibility",
        checklist: "Checklist",
        forms: "Forms",
        review: "Review",
        packet: "Packet",
      },
      badges: {
        intake: "Intake in progress",
        eligibility: "Checking eligibility",
        checklist: "Checklist building",
        forms: "Forms generated",
        review: "Consistency check",
        packet: "Ready to file",
      },
      intake: {
        question: "Question 4 of 12",
        prompt: "Which visa category are you applying for?",
        answer: "Engineer / Specialist in Humanities",
      },
      eligibility: {
        checks: [
          "Sponsor company registered with Immigration Bureau",
          "Salary meets category threshold",
          "No prior denial on record",
        ],
        result: "Eligible for this category",
      },
      checklist: {
        coeTitle: "Certificate of Eligibility",
        coeStatus: "Uploaded · verified against Immigration Bureau guidance",
        employmentTitle: "Certificate of Employment",
        employmentStatus: "Requested from HR",
      },
      forms: {
        fields: [
          { label: "Full name", value: "Yuki Tanaka" },
          { label: "Employer", value: "Nikko Systems K.K." },
          { label: "Visa category", value: "Engineer / Specialist in Humanities" },
        ],
        ready: "Ready",
      },
      review: {
        checking: "Cross-checking 14 fields across 3 forms…",
        checks: ["Name matches across all forms", "Dates consistent with intake"],
        result: "No conflicts found",
      },
      packet: {
        filename: "Visa_Packet_JP-WORK-2049.pdf",
        meta: "2.4 MB · 9 pages · submission-ready",
      },
    },
    jurisdictions: {
      eyebrow: "Built jurisdiction by jurisdiction, not all at once",
      inProgress: "In progress",
      items: {
        jp: { name: "Japan", detail: "Work visa · tourist visa (J3) · renewal & new application" },
        us: { name: "United States", detail: "H-1B specialty worker · tourist / visitor visa (B1/B2)" },
        uk: { name: "United Kingdom", detail: "Standard visitor visa · work & study" },
      },
    },
    howItWorks: {
      eyebrow: "How it works",
      titleBefore: "From “where do I start” to a packet ",
      titleAccent: "ready to file",
      titleAfter: ".",
      body: "Four stages, one case. Skip nothing your filing needs, and see nothing it doesn't.",
      stages: {
        scope: {
          title: "Scope your case",
          body: "Pick your country, visa category, and what you need to do — renew, change status, or file new. Only supported combinations are shown.",
        },
        intake: {
          title: "Answer a branching intake",
          body: "Questions adapt to what you've already told us. Save at any point and resume later — nothing is timed, nothing is lost.",
        },
        eligibility: {
          title: "See eligibility and your checklist",
          body: "Your answers are checked against published eligibility criteria, then turned into a personalized document checklist — why each item is required and how to get it.",
        },
        forms: {
          title: "Get forms, review, submit",
          body: "Official government forms are auto-filled from your intake, checked for consistency, and assembled into a submission-ready packet.",
        },
      },
    },
    features: {
      eyebrow: "Why Torii",
      title: "Built for a high-stakes, form-heavy process.",
      items: {
        sourced: {
          title: "Every instruction is sourced",
          body: "Eligibility checks and checklist items link back to the exact official government page they came from. If it can't be cited, we don't show it.",
        },
        forms: {
          title: "Auto-filled official forms",
          body: "Your intake data flows straight into the right government form — version-tracked, with missing required fields flagged before you file.",
        },
        branching: {
          title: "Branching intake, not a static PDF",
          body: "Every question depends on your last answer. You only ever see the fields your specific case needs.",
        },
        save: {
          title: "Save and resume, anytime",
          body: "Close the tab, come back next week. Your case picks up exactly where you left it, at whatever step you reached.",
        },
        language: {
          title: "In your language, and theirs",
          body: "Every step is shown in your language and the host country's, with the official term always kept alongside so nothing gets lost in translation.",
        },
        escalate: {
          title: "Never stuck alone",
          body: "The moment a case needs professional judgment, escalate in-context to a licensed professional — with your consent, not automatically.",
        },
      },
      coePreview: {
        title: "Certificate of Eligibility",
        body: "Required because your visa category mandates pre-approval.",
        source: "Immigration Bureau of Japan",
      },
      formPreview: {
        code: "COE-7",
        version: "v2024.1",
        ready: "Ready",
      },
    },
    trust: {
      eyebrow: "Guided prep, not legal advice",
      title: "Software that knows the edge of what it should decide.",
      body: "Torii is not a law firm and doesn't practice law. It applies published, sourced eligibility rules to your case — and the moment something falls outside those rules, it says so instead of guessing.",
      points: [
        {
          strong: "Prior denials, criminal history, unusual employment",
          rest: " — anything outside published rules gets flagged, not papered over.",
        },
        {
          strong: "You choose to escalate.",
          rest: " Your case is only shared with a licensed professional if you give consent.",
        },
        {
          strong: "A fraction of a traditional attorney's fee",
          rest: " for the cases that don't need one.",
        },
      ],
      card: {
        title: "Escalate this case",
        badge: "Needs review",
        reasonLabel: "Reason",
        reason: "Prior visa denial in 2022",
        messageLabel: "Message to reviewer",
        message: "“My H-1B was denied two years ago for a different employer — does that affect this renewal?”",
        consent: "I consent to sharing this case with a licensed reviewer",
        sent: "Sent to review queue",
      },
    },
    pricing: {
      eyebrow: "Pricing",
      title: "Priced per case, not by the month.",
      body: "No subscriptions to cancel. Pay when you're ready to file, and only for what your case actually needs.",
      perCase: "per case",
      free: "Free",
      popular: "Most cases",
      tiers: [
        {
          id: "scope",
          name: "Scope check",
          price: "Free",
          description: "See your eligibility and checklist before you commit to anything.",
          features: [
            "Country & visa category selection",
            "Branching eligibility questions",
            "Personalized document checklist",
            "No credit card required",
          ],
          cta: "Start free",
        },
        {
          id: "guided",
          name: "Guided filing",
          price: "$149",
          description: "Everything you need to file it yourself, correctly.",
          features: [
            "Everything in Scope check",
            "Full branching intake",
            "Auto-filled official forms",
            "Pre-submission consistency check",
            "Submission-ready packet",
          ],
          cta: "Start your case",
        },
        {
          id: "review",
          name: "Attorney review",
          price: "$349",
          description: "For cases that need a second set of eyes.",
          features: [
            "Everything in Guided filing",
            "Priority escalation to a licensed professional",
            "Case review before you file",
            "Direct message thread with your reviewer",
          ],
          cta: "Talk to a professional",
        },
      ],
      footnote:
        "Prices shown are per case, not recurring subscriptions, and vary by jurisdiction and visa category. Attorney review is provided by independent licensed professionals, not by Torii.",
    },
    blog: {
      eyebrow: "From the blog",
      title: "Notes on filing it yourself, correctly.",
      body: "Short, practical reads on how Torii works and what actually trips people up in a filing.",
      readTime: "min read",
      viewAll: "View all posts",
      readMore: "Read more",
    },
    ctaBand: {
      title: "Start with your country and visa type.",
      body: "Two minutes to scope your case. No commitment — see your checklist before you decide anything else.",
      cta: "Start your case",
    },
    faq: {
      titleBefore: "Questions worth answering ",
      titleAccent: "plainly",
      items: {
        lawFirm: {
          question: "Is Torii a law firm, or does it give legal advice?",
          answer:
            "No. Torii is guided form-preparation software. It helps you prepare your own filing using published government rules, and it is not a substitute for a licensed immigration attorney or accredited representative. When a case needs professional judgment, Torii routes you to one.",
        },
        sourceOfGuidance: {
          question: "Where does the guidance in Torii come from?",
          answer:
            "Every eligibility check and checklist item is sourced to the official government page it was drawn from — you can open that page yourself at any point. Torii does not assert requirements it can't cite.",
        },
        supportedJurisdictions: {
          question: "Which countries and visa types are supported?",
          answer:
            "Torii is built jurisdiction by jurisdiction rather than all at once, so each one is genuinely complete before it goes live. Today that means Bangladesh to Japan, United States, and the United Kingdom, with more jurisdictions and categories rolling out after.",
        },
        complexCase: {
          question: "What happens if my case is more complicated than a checklist?",
          answer:
            "You can escalate at any step — prior denials, criminal history flags, unusual employment situations, anything outside the published rules. Escalating shares your case with a licensed professional only with your explicit consent.",
        },
        saveResume: {
          question: "Can I stop partway through and finish later?",
          answer:
            "Yes. Every answer you give is saved as you go. Come back whenever you're ready and Torii resumes at the exact step you left — intake, eligibility, checklist, forms, review, or packet.",
        },
        finalOutput: {
          question: "What do I get at the end?",
          answer:
            "A submission-ready packet: your auto-filled, version-tracked forms plus your completed document checklist, assembled after a pre-submission consistency check — ready to file or hand to your representative.",
        },
      },
    },
    footer: {
      title: "File it yourself. Correctly.",
      cta: "Start your case",
      disclaimer:
        "Torii is a working codename. Guided form preparation — not legal advice. Every instruction is sourced to the official government page it came from.",
    },
  },
  ja: {
    nav: {
      howItWorks: "利用の流れ",
      features: "特長",
      pricing: "料金",
      blog: "ブログ",
      faq: "よくある質問",
      signIn: "ログイン",
      dashboard: "ダッシュボード",
      startCase: "申請を始める",
    },
    hero: {
      eyebrow: "ビザ・在留資格申請を伴走サポート",
      titleBefore: "ビザ申請を",
      titleAccent: "正しく",
      titleAfter: "。弁護士費用のごく一部で。",
      body: "Toriiは「どの書類が必要かわからない」という状態から、提出できる状態の申請一式まで案内します。分岐式のヒアリング、あなた専用の必要書類チェックリスト、政府書式への自動入力——すべてのステップに、根拠となる公式ページの出典が付きます。",
      ctaPrimary: "申請を始める",
      ctaSecondary: "利用の流れを見る",
      disclaimerBefore: "Toriiは",
      disclaimerStrong: "法律専門家ではありません",
      disclaimerAfter:
        "。ご自身での申請準備をサポートし、専門的な判断が必要になった時点で有資格の専門家におつなぎします。",
    },
    heroDemo: {
      caseId: "JP-WORK-2049",
      locale: "日本語 · ライブデモ",
      steps: {
        intake: "ヒアリング",
        eligibility: "資格確認",
        checklist: "チェックリスト",
        forms: "書式作成",
        review: "レビュー",
        packet: "申請一式",
      },
      badges: {
        intake: "ヒアリング中",
        eligibility: "資格を確認中",
        checklist: "チェックリスト作成中",
        forms: "書式を生成しました",
        review: "整合性を確認中",
        packet: "提出準備完了",
      },
      intake: {
        question: "質問 4 / 12",
        prompt: "申請するビザの種類は？",
        answer: "技術・人文知識・国際業務",
      },
      eligibility: {
        checks: [
          "所属企業が入管に登録されていることを確認",
          "給与が該当カテゴリーの基準を満たしている",
          "過去に不許可歴がない",
        ],
        result: "このカテゴリーの要件を満たしています",
      },
      checklist: {
        coeTitle: "在留資格認定証明書",
        coeStatus: "アップロード済み · 入国管理局の案内に基づき確認済み",
        employmentTitle: "在職証明書",
        employmentStatus: "人事部に依頼済み",
      },
      forms: {
        fields: [
          { label: "氏名", value: "田中 由紀" },
          { label: "勤務先", value: "日光システムズ株式会社" },
          { label: "ビザの種類", value: "技術・人文知識・国際業務" },
        ],
        ready: "準備完了",
      },
      review: {
        checking: "3つの書式・14項目を照合中…",
        checks: ["全書式で氏名が一致", "ヒアリング内容と日付が一致"],
        result: "不整合はありませんでした",
      },
      packet: {
        filename: "申請一式_JP-WORK-2049.pdf",
        meta: "2.4 MB · 9ページ · 提出準備完了",
      },
    },
    jurisdictions: {
      eyebrow: "国・地域ごとに、着実に対応を広げています",
      inProgress: "準備中",
      items: {
        jp: { name: "日本", detail: "就労ビザ・観光ビザ（J3）· 更新・新規申請" },
        us: { name: "アメリカ合衆国", detail: "H-1B専門職ビザ · 観光/短期商用ビザ (B1/B2)" },
        uk: { name: "イギリス（英国）", detail: "標準ビザ · 就労・留学ビザ" },
      },
    },
    howItWorks: {
      eyebrow: "利用の流れ",
      titleBefore: "「何から始めればいいか」から、",
      titleAccent: "提出できる状態",
      titleAfter: "の申請一式まで。",
      body: "4つのステップで、1つの申請を。必要なことは省かず、不要なことは見せません。",
      stages: {
        scope: {
          title: "申請内容を選ぶ",
          body: "国・ビザの種類・目的（更新・変更・新規申請）を選択します。対応している組み合わせのみが表示されます。",
        },
        intake: {
          title: "分岐式のヒアリングに回答",
          body: "質問はそれまでの回答に応じて変化します。いつでも保存して後から再開でき、時間制限もありません。",
        },
        eligibility: {
          title: "資格確認とチェックリストを確認",
          body: "回答は公表されている審査基準と照合され、あなた専用の必要書類チェックリストに変換されます。各項目がなぜ必要か、どう取得するかも表示されます。",
        },
        forms: {
          title: "書式を作成し、レビューして提出",
          body: "公式の政府書式はヒアリング内容から自動入力され、整合性を確認したうえで提出準備の整った一式にまとめられます。",
        },
      },
    },
    features: {
      eyebrow: "Toriiが選ばれる理由",
      title: "書類が多く、失敗が許されないプロセスのために。",
      items: {
        sourced: {
          title: "すべての案内に出典があります",
          body: "資格確認とチェックリストの各項目は、根拠となる公式の政府ページに紐づいています。出典を示せない情報は表示しません。",
        },
        forms: {
          title: "公式書式への自動入力",
          body: "ヒアリング内容がそのまま該当する政府書式に反映されます。バージョンも管理され、提出前に未入力項目があれば知らせます。",
        },
        branching: {
          title: "固定のPDFではなく、分岐式のヒアリング",
          body: "すべての質問は直前の回答に応じて変化します。あなたの申請に本当に必要な項目だけが表示されます。",
        },
        save: {
          title: "いつでも保存・再開",
          body: "タブを閉じて、来週また戻ってきても大丈夫です。申請は中断した場所から正確に再開されます。",
        },
        language: {
          title: "あなたの言語でも、相手国の言語でも",
          body: "すべてのステップはあなたの言語と申請先の言語で表示され、公式用語は常に併記されるため、訳による取りこぼしがありません。",
        },
        escalate: {
          title: "一人で悩ませません",
          body: "専門的な判断が必要になった時点で、その場から有資格の専門家にエスカレーションできます——同意した場合のみ、自動ではありません。",
        },
      },
      coePreview: {
        title: "在留資格認定証明書",
        body: "申請するビザの種類が事前認定を必須としているため必要です。",
        source: "日本国 出入国在留管理庁",
      },
      formPreview: {
        code: "COE-7",
        version: "v2024.1",
        ready: "準備完了",
      },
    },
    trust: {
      eyebrow: "申請準備のサポートであり、法律相談ではありません",
      title: "判断すべき範囲の境界をわきまえたソフトウェア。",
      body: "Toriiは法律事務所ではなく、法律業務も行いません。公表されている根拠のある審査基準をあなたの申請に適用し、その基準から外れる事態が生じた時点で、推測せずにそう伝えます。",
      points: [
        {
          strong: "過去の不許可歴、犯罪歴、特殊な雇用形態など",
          rest: "——公表基準の範囲外にあたる事項は、隠さずにフラグとして表示します。",
        },
        {
          strong: "エスカレーションはあなたが選びます。",
          rest: "あなたが同意した場合にのみ、有資格の専門家に申請内容が共有されます。",
        },
        {
          strong: "従来の弁護士費用のごく一部",
          rest: "で、専門家が不要な申請に対応します。",
        },
      ],
      card: {
        title: "この申請をエスカレーション",
        badge: "要レビュー",
        reasonLabel: "理由",
        reason: "2022年にビザが不許可となった経歴あり",
        messageLabel: "レビュー担当者へのメッセージ",
        message: "「2年前、別の雇用主のもとでH-1Bが不許可になりました。今回の更新に影響しますか？」",
        consent: "有資格のレビュー担当者へこの申請を共有することに同意します",
        sent: "レビューキューに送信しました",
      },
    },
    pricing: {
      eyebrow: "料金",
      title: "月額制ではなく、申請ごとの料金です。",
      body: "解約が必要なサブスクリプションはありません。申請の準備が整ったときに、必要な分だけお支払いいただきます。",
      perCase: "申請ごと",
      free: "無料",
      popular: "多くの方に選ばれています",
      tiers: [
        {
          id: "scope",
          name: "資格チェック",
          price: "無料",
          description: "何かを決める前に、資格確認とチェックリストを確認できます。",
          features: [
            "国・ビザの種類の選択",
            "分岐式の資格確認ヒアリング",
            "あなた専用の必要書類チェックリスト",
            "クレジットカード登録不要",
          ],
          cta: "無料で始める",
        },
        {
          id: "guided",
          name: "ガイド付き申請",
          price: "$149",
          description: "自分自身で正しく申請するために必要なすべてが揃います。",
          features: [
            "資格チェックの内容をすべて含む",
            "分岐式ヒアリングをすべて実施",
            "公式書式への自動入力",
            "提出前の整合性チェック",
            "提出準備の整った申請一式",
          ],
          cta: "申請を始める",
        },
        {
          id: "review",
          name: "専門家レビュー",
          price: "$349",
          description: "第三者の目によるチェックが必要な申請向けです。",
          features: [
            "ガイド付き申請の内容をすべて含む",
            "有資格専門家への優先エスカレーション",
            "提出前の申請内容レビュー",
            "レビュー担当者との直接メッセージ",
          ],
          cta: "専門家に相談する",
        },
      ],
      footnote:
        "表示価格は申請ごとの料金であり、継続課金のサブスクリプションではありません。国・ビザの種類により異なります。専門家レビューはToriiではなく、独立した有資格の専門家により提供されます。",
    },
    blog: {
      eyebrow: "ブログ",
      title: "自分自身で正しく申請するためのノート。",
      body: "Toriiの仕組みと、申請でつまずきやすいポイントについての短い実用的な記事です。",
      readTime: "分で読了",
      viewAll: "すべての記事を見る",
      readMore: "続きを読む",
    },
    ctaBand: {
      title: "まずは国とビザの種類を選ぶだけ。",
      body: "申請内容の確認はわずか2分。決断は不要です——まずはチェックリストを見てから考えられます。",
      cta: "申請を始める",
    },
    faq: {
      titleBefore: "疑問に、",
      titleAccent: "率直に",
      items: {
        lawFirm: {
          question: "Toriiは法律事務所ですか？法律相談はできますか？",
          answer:
            "いいえ。Toriiは申請書類の準備をガイドするソフトウェアです。公表されている政府の規則に基づき、ご自身での申請準備をサポートするものであり、有資格の移民弁護士や認定代理人の代わりにはなりません。専門的な判断が必要な申請は、専門家へおつなぎします。",
        },
        sourceOfGuidance: {
          question: "Toriiの案内内容はどこから得ていますか？",
          answer:
            "資格確認とチェックリストの各項目は、根拠となる公式の政府ページに紐づいており、いつでもそのページをご自身で開くことができます。Toriiは出典を示せない要件を主張することはありません。",
        },
        supportedJurisdictions: {
          question: "対応している国・ビザの種類は？",
          answer:
            "Toriiは一度にすべてではなく、国・地域ごとに着実に対応を広げています。現在はバングラデシュ発の日本、アメリカ、イギリスへの申請に対応しており、今後さらに国とビザの種類が追加される予定です。",
        },
        complexCase: {
          question: "チェックリストだけでは対応しきれない場合はどうなりますか？",
          answer:
            "どのステップからでもエスカレーションできます——過去の不許可歴、犯罪歴のフラグ、特殊な雇用形態など、公表基準の範囲外にあたる事項が対象です。エスカレーションによる申請内容の共有は、明示的な同意があった場合にのみ行われます。",
        },
        saveResume: {
          question: "途中で中断して、後から続きを行うことはできますか？",
          answer:
            "はい。入力した回答はその都度保存されます。いつでも戻ってきていただければ、中断した正確なステップ——ヒアリング、資格確認、チェックリスト、書式作成、レビュー、申請一式のいずれか——から再開します。",
        },
        finalOutput: {
          question: "最終的に何が得られますか？",
          answer:
            "提出準備の整った申請一式です。自動入力・バージョン管理された書式と、完成した必要書類チェックリストが、提出前の整合性チェックを経て、そのまま提出または代理人へ引き渡せる状態でまとまります。",
        },
      },
    },
    footer: {
      title: "自分自身で、正しく申請する。",
      cta: "申請を始める",
      disclaimer:
        "Toriiは開発中のプロジェクト名です。申請書類準備のガイドであり、法律相談ではありません。すべての案内には、根拠となる公式の政府ページの出典が付きます。",
    },
  },
};

export type Dictionary = typeof dictionary.en;
