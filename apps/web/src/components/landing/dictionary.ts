export const dictionary = {
  en: {
    nav: {
      outcomes: "What you get",
      howItWorks: "How it works",
      coverage: "Supported visas",
      features: "Features",
      pricing: "Pricing",
      blog: "Blog",
      faq: "FAQ",
      signIn: "Sign in",
      dashboard: "Dashboard",
      startCase: "Start your case",
      headerCta: "Check eligibility",
    },
    cta: {
      startFree: "Start free — 3 passes included",
      stickyCta: "Start free — 3 passes",
      reassure: ["Free eligibility check", "No credit card needed", "Save anytime and resume"],
      returningBefore: "Already started a case? ",
      returningLink: "Sign in",
    },
    dashboardShowcase: {
      eyebrow: "Interactive Demo // See It In Action",
      title: "See your visa forms created in real time",
      subtitle:
        "As you answer simple questions, Torii checks official Japanese immigration rules and fills out your government forms on the spot.",
      tabs: {
        renewal: "Work Visa Renewal (JP-2026-000047)",
        change: "Student to Work Visa (JP-2026-000048)",
        coe: "New Work Visa CoE (JP-2026-000045)",
      },
      stats: {
        active: "Active Cases",
        formsReady: "Statutory Forms Ready",
        accuracy: "Statutory Rule Match",
        rejections: "0 Discrepancy Risk",
      },
    },
    outcomes: {
      eyebrow: "What you walk away with",
      title: "Not advice. Documents.",
      body: "Four things end up in your hands, and every one of them traces back to the official page that required it.",
      items: [
        {
          title: "Your official form, filled",
          body: "The statutory sheet your procedure actually requires, filled from your answers and left blank wherever you have not answered. Nothing is guessed on a document you sign.",
        },
        {
          title: "A checklist that cites its source",
          body: "Every document your case needs, why it is required, and a link to the government page that says so — so you can check anything Torii tells you.",
        },
        {
          title: "Drafts you can finish and sign",
          body: "Cover letter, statement of purpose, schedule of stay. Download them as a PDF to file, or as a Word file to edit in your own words first.",
        },
        {
          title: "A plan with real lead times",
          body: "What to start today, how long a bank letter or a police certificate actually takes, and the things that get applications handed back at the counter.",
        },
      ],
      sourcesLabel: "Requirements come from the authorities themselves",
      sources: [
        "Immigration Services Agency of Japan (出入国在留管理庁)",
        "Ministry of Justice (法務省)",
        "Ministry of Foreign Affairs (外務省)",
      ],
    },
    hero: {
      eyebrow: "🇯🇵 Japan Visa Assistant · Official 2026 Rules · Free Check",
      titleBefore: "Get your Japan visa paperwork done ",
      titleAccent: "right",
      titleAfter: " — without expensive lawyer fees.",
      body: "Answer simple questions online. Torii checks official Japanese immigration rules, fills out your government forms automatically, and catches mistakes before you submit. 100% free to start.",
      ctaPrimary: "Start free — 3 passes included",
      ctaSecondary: "See how it works ↓",
      disclaimerBefore: "Torii is ",
      disclaimerStrong: "not a legal advisor",
      disclaimerAfter:
        " — it helps you prepare your own filing, and routes you to a licensed professional the moment your case needs one.",
    },
    heroDemo: {
      caseId: "JP-2026-000047",
      locale: "Japan · Work Visa (Renewal) · Official Forms",
      steps: {
        intake: "Intake",
        eligibility: "Rules",
        checklist: "Checklist",
        forms: "Forms",
        review: "Review",
        packet: "File",
      },
      badges: {
        intake: "Intake (87% done)",
        eligibility: "Requirements Passed ✓",
        checklist: "Checklist (7/8 ready)",
        forms: "Official Forms Ready",
        review: "0 Mistakes Found",
        packet: "Ready to Submit",
      },
      intake: {
        question: "Your Job in Japan",
        prompt: "What is your sponsoring employer's 13-digit Corporate Number (法人番号)?",
        answer: "Nikko Systems K.K. (5010001029384)",
      },
      eligibility: {
        checks: [
          "Sponsoring company meets official immigration standards",
          "Salary meets the legal minimum requirement (¥220,000+/mo)",
          "No tax arrears or immigration issues found",
        ],
        result: "You qualify for a 1 to 3 year visa extension",
      },
      checklist: {
        coeTitle: "Passport & Residence Card (Originals)",
        coeStatus: "Verified against immigration standards · Valid through Dec 2026",
        employmentTitle: "Proof of Employment & Tax Withholding Slip",
        employmentStatus: "Checked against National Tax Agency standards",
      },
      forms: {
        fields: [
          { label: "Application Form", value: "Visa Extension Form (Work Visa)" },
          { label: "Applicant Name", value: "Kenji Tanaka" },
          { label: "Sponsor Entity", value: "Nikko Systems K.K. (Category 3)" },
        ],
        ready: "Official Ministry PDF Ready",
      },
      review: {
        checking: "Checking all 42 fields against official rules…",
        checks: [
          "Name and birthdate match on passport and residence card",
          "Salary and job duties match your employment contract",
          "Application window confirmed: Window open, no grace period needed",
        ],
        result: "All checks passed · 0 mistakes found",
      },
      packet: {
        filename: "JP-2026-000047_Filing_Packet.pdf",
        meta: "Official format for Tokyo Immigration Bureau · Ready to file",
      },
    },
    coverage: {
      eyebrow: "Supported Japan Visas",
      title: "Covering the most common Japan visa routes.",
      body: "Whether you are working, studying, or joining family in Japan, Torii has the right official forms and checklists.",
      routes: {
        work: { name: "Work visa", detail: "Engineer / Specialist in Humanities / International Services" },
        student: { name: "Student visa", detail: "University, college or language school" },
        tourist: { name: "Tourist / Temporary Visitor", detail: "Short-term travel, business, visiting relatives" },
        dependent: { name: "Dependent visa", detail: "Spouse and children of work or student residents" },
        spouse: { name: "Spouse or child of a Japanese national or PR", detail: "日本人の配偶者等 / 永住者の配偶者等" },
      },
      more: "More countries on the way",
    },
    howItWorks: {
      eyebrow: "Simple 4-Step Process",
      titleBefore: "From “where do I start” to ",
      titleAccent: "ready to file",
      titleAfter: " in 4 simple steps.",
      body: "No confusing legal jargon. Just step-by-step guidance for your Japan visa.",
      stages: {
        scope: {
          title: "Pick your visa",
          body: "Choose your visa type and what you need: renew your visa, switch to a new status, or apply fresh.",
        },
        intake: {
          title: "Answer simple questions",
          body: "Clear questions in plain English. Save at any point and finish later — nothing is lost.",
        },
        eligibility: {
          title: "See if you qualify, and get your checklist",
          body: "See if you qualify instantly, plus a customized checklist of every document you need to bring.",
        },
        forms: {
          title: "Download completed government forms",
          body: "Your official Ministry of Justice forms are filled out automatically and checked for mistakes before you submit.",
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
      eyebrow: "Transparent Pricing // Pay per Pass",
      title: "No subscriptions. Priced per application pass.",
      body: "1 Credit = 1 Full Application Pass. All official Ministry of Justice forms, AI statutory guidance, and OCR document extraction are fully included. Pay once, use whenever you need.",
      perCase: "pass",
      free: "Free",
      welcomeBonus: {
        badge: "🎁 Welcome Bonus",
        title: "3 Complimentary Passes on Registration",
        body: "Every registered user receives 3 full application passes to prepare and test filings at zero cost.",
      },
      currencyLabel: "Currency:",
      tiers: [
        {
          id: "free",
          name: "Free Eligibility & Starter",
          price_usd: "$0",
          price_jpy: "¥0",
          unit_usd: "Free Forever · No Card",
          unit_jpy: "永年無料 · カード不要",
          credits: 3,
          badge: "Free Forever",
          description: "Check your eligibility against statutory criteria and test filings with 3 complimentary passes.",
          features: [
            "3 Complimentary Application Passes (Welcome Bonus)",
            "Full statutory eligibility check (Japan routes)",
            "Personalized official document checklist",
            "Interactive branching questionnaire",
            "Save & resume case progress anytime",
            "No credit card required",
          ],
          cta: "Start Free — 3 Passes",
        },
        {
          id: "starter",
          name: "1 Full Application Pass",
          price_usd: "$19",
          price_jpy: "¥2,800",
          unit_usd: "$19 / case",
          unit_jpy: "¥2,800 / 件",
          credits: 1,
          badge: null,
          description: "Complete filing kit for 1 visa application. Everything needed to prepare and file correctly.",
          features: [
            "1 Full Application Pass (1 Credit)",
            "All OCR scans & document data extraction",
            "AI statutory copilot & compliance guidance",
            "Official Ministry of Justice (MOJ) PDF generation",
            "Pre-submission consistency audit (0 errors)",
            "Submission-ready packet (.PDF & editable .DOCX)",
          ],
          cta: "Get 1 Pass — $19",
        },
        {
          id: "standard",
          name: "3-Application Bundle",
          price_usd: "$39",
          price_jpy: "¥5,800",
          unit_usd: "$13.00 / case · Save 32%",
          unit_jpy: "¥1,930 / 件 · 32%お得",
          credits: 3,
          badge: "Popular · Save 32%",
          description: "Ideal for renewals, spouses, families, or preparing multiple visa routes.",
          features: [
            "3 Full Application Passes (3 Credits)",
            "Everything in the 1-Pass kit",
            "Family & dependent joint filing support",
            "Re-usable profile & corporate sponsor data",
            "Priority statutory discrepancy audit",
            "Save $18 compared to single passes",
          ],
          cta: "Get 3 Passes — $39",
        },
        {
          id: "family",
          name: "5-Application Agency Pack",
          price_usd: "$59",
          price_jpy: "¥8,900",
          unit_usd: "$11.80 / case · Save 38%",
          unit_jpy: "¥1,780 / 件 · 38%お得",
          credits: 5,
          badge: "Best Value · Save 38%",
          description: "For employers, HR teams, agencies, or multi-year visa roadmaps.",
          features: [
            "5 Full Application Passes (5 Credits)",
            "Everything in the 3-Pass bundle",
            "Corporate sponsor sheet (所属機関等作成用) bulk mapping",
            "Multi-year status renewal tracking",
            "Team & agency dossier export tools",
            "Save $36 compared to single passes",
          ],
          cta: "Get 5 Passes — $59",
        },
      ],
      footnote:
        "Prices are one-time payments per application pass, not recurring monthly subscriptions. 1 Credit = 1 Full Visa Application Dossier. All registered users receive 3 complimentary passes on signup. Official Ministry of Justice and Immigration Services Agency forms are version-tracked for 2026.",
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
      title: "Ready to get your Japan visa sorted?",
      body: "Take 2 minutes to check if you qualify. Create your free account and get 3 free application passes today. No credit card needed.",
      cta: "Start free — 3 passes included",
    },
    faq: {
      titleBefore: "Questions worth answering ",
      titleAccent: "plainly",
      help: {
        title: "Still deciding?",
        body: "The blog goes further on how sourcing works and which documents actually delay a Japan filing.",
        cta: "Read the notes",
      },
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
            "Japan, today — work (技術・人文知識・国際業務), student (留学), short-stay tourist and family visit (短期滞在), dependent (家族滞在), and spouse or child of a Japanese national or permanent resident, for new applications, renewals and changes of status. Torii is built one country at a time so each is genuinely complete before it goes live; more are on the way.",
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
      cta: "Start free — 3 passes included",
      tagline: "Guided Japan visa preparation, sourced to the authorities that publish the rules.",
      createAccount: "Create account",
      groups: {
        product: "Product",
        routes: "Visa routes",
        resources: "Resources",
      },
      disclaimer:
        "Torii is a working codename. Guided form preparation — not legal advice. Every instruction is sourced to the official government page it came from.",
    },
  },
  ja: {
    nav: {
      outcomes: "得られるもの",
      howItWorks: "利用の流れ",
      coverage: "対応ビザ",
      features: "特長",
      pricing: "料金",
      blog: "ブログ",
      faq: "よくある質問",
      signIn: "ログイン",
      dashboard: "ダッシュボード",
      startCase: "申請を始める",
      headerCta: "適格性をチェック",
    },
    cta: {
      startFree: "無料で適格性をチェック",
      stickyCta: "無料で適格性をチェック",
      reassure: ["適格性チェックは無料", "クレジットカード不要", "いつでも中断・再開"],
      returningBefore: "すでに申請を始めていますか？ ",
      returningLink: "ログイン",
    },
    dashboardShowcase: {
      eyebrow: "リアルタイム申請管理 // コマンドセンター",
      title: "Toriiによる申請管理ワークフロー",
      subtitle:
        "回答を入力するたびに法令基準と照合され、公式書式と提出書類チェックリストがリアルタイムに生成されます。",
      tabs: {
        renewal: "就労ビザ更新 (JP-2026-000047)",
        change: "資格変更: 留学→就労 (JP-2026-000048)",
        coe: "在留資格認定 CoE (JP-2026-000045)",
      },
      stats: {
        active: "進行中の申請",
        formsReady: "作成済み法定書式",
        accuracy: "法定基準適合率",
        rejections: "窓口差し戻しリスク 0",
      },
    },
    outcomes: {
      eyebrow: "手元に残るもの",
      title: "アドバイスではなく、書類を。",
      body: "4つの成果物が手元に残ります。そのすべてが、根拠となる公式ページまでたどれます。",
      items: [
        {
          title: "記入済みの公式書式",
          body: "手続きに実際に必要な法定様式に、あなたの回答をそのまま反映します。未回答の欄は空欄のまま——署名する書類に推測を書き込むことはありません。",
        },
        {
          title: "出典付きのチェックリスト",
          body: "必要な書類、その理由、そして根拠となる政府ページへのリンク。Toriiの説明はすべてご自身で確認できます。",
        },
        {
          title: "仕上げて署名できる下書き",
          body: "カバーレター、理由書、滞在予定表。提出用のPDFで、あるいはご自身の言葉に直せるWord形式で書き出せます。",
        },
        {
          title: "所要期間まで含めた計画",
          body: "今日から動くべきこと、残高証明書や無犯罪証明書に実際かかる期間、そして窓口で申請が差し戻される原因。",
        },
      ],
      sourcesLabel: "要件はすべて、当局の公式ページから",
      sources: ["出入国在留管理庁", "法務省", "外務省"],
    },
    hero: {
      eyebrow: "出入国在留管理庁 2026年最新法令基準適合 · 無料適格性判定",
      titleBefore: "ビザ申請は、こんなに",
      titleAccent: "ややこしい",
      titleAfter: "必要はありません。費用も同じです。",
      body: "Toriiが、日本が求める書類を正確に示し、あなたの回答から公式書式を作成し、窓口で申請が差し戻される原因になるミスを事前に見つけます。お支払いの前に、まず適格性をご確認ください。",
      ctaPrimary: "無料で適格性をチェック",
      ctaSecondary: "利用の流れを見る",
      disclaimerBefore: "Toriiは",
      disclaimerStrong: "法律専門家ではありません",
      disclaimerAfter:
        "。ご自身での申請準備をサポートし、専門的な判断が必要になった時点で有資格の専門家におつなぎします。",
    },
    heroDemo: {
      caseId: "JP-2026-000047",
      locale: "日本 · 就労ビザ (技術・人文知識・国際業務) · 在留期間更新",
      steps: {
        intake: "ヒアリング",
        eligibility: "資格確認",
        checklist: "チェックリスト",
        forms: "申請書式",
        review: "整合性審査",
        packet: "申請一式",
      },
      badges: {
        intake: "ヒアリング (87%完了)",
        eligibility: "出入国在留管理庁 基準適合",
        checklist: "チェックリスト (7/8確認済)",
        forms: "法務省正規様式 作成完了",
        review: "不整合・記載漏れ 0件",
        packet: "窓口・オンライン提出準備完了",
      },
      intake: {
        question: "所属機関・企業情報",
        prompt: "所属機関の13桁の法人番号を入力してください：",
        answer: "日光システムズ株式会社 (5010001029384)",
      },
      eligibility: {
        checks: [
          "所属機関が「カテゴリー3」の公表基準に適合",
          "月額報酬が法定基準額（22万円以上）を充足",
          "税金・公的年金等の滞納・入管法違反履歴なし",
        ],
        result: "在留期間更新（1年〜3年）の要件を充足",
      },
      checklist: {
        coeTitle: "旅券及び在留カード (原本提示)",
        coeStatus: "出入国在留管理庁 基準照合完了 · 2026年12月有効期限",
        employmentTitle: "在職証明書 及び 前年分の給与所得の源泉徴収票",
        employmentStatus: "国税庁法定調書基準と照合完了",
      },
      forms: {
        fields: [
          { label: "申請書式", value: "在留期間更新許可申請書 (技術・人文知識・国際業務)" },
          { label: "申請人", value: "田中 由紀 (Tanaka Yuki)" },
          { label: "所属機関", value: "日光システムズ株式会社 (カテゴリー3)" },
        ],
        ready: "法務省 標準様式PDF",
      },
      review: {
        checking: "提出書類とヒアリング回答の全42項目をクロスチェック中…",
        checks: [
          "旅券・在留カード記載の氏名・生年月日・国籍が完全一致",
          "職務内容および報酬額が雇用契約書の記載内容と整合",
          "申請期限確認済：更新受付期間内（在留期限3ヶ月前）・猶予期間なし警告済",
        ],
        result: "提出前整合性チェック完了 · 不整合 0件",
      },
      packet: {
        filename: "JP-2026-000047_提出書類一式.pdf",
        meta: "東京出入国在留管理局 提出仕様準拠 · 印刷または電子申請対応",
      },
    },
    coverage: {
      eyebrow: "現在の対応：日本",
      title: "対応している日本のビザ",
      body: "Toriiは一度に何か国も広げず、まず一つの国を完成させます。新規申請・更新・在留資格変更に対応しています。",
      routes: {
        work: { name: "就労ビザ", detail: "技術・人文知識・国際業務" },
        student: { name: "留学ビザ", detail: "大学・専門学校・日本語学校" },
        tourist: { name: "短期滞在", detail: "観光・商用・知人訪問" },
        dependent: { name: "家族滞在", detail: "就労・留学ビザ保持者の配偶者と子" },
        spouse: { name: "日本人の配偶者等", detail: "日本人・永住者の配偶者等" },
      },
      more: "他の国も準備中です",
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
      eyebrow: "明朗な料金体系 // 申請パス制",
      title: "月額サブスクなし。1件ごとの申請パス制。",
      body: "1クレジット＝1件のビザ申請完全パスです。法務省・出入国在留管理庁の公的書式出力、AI法令相談、OCR書類抽出のすべてが含まれます。必要な分だけ1回限りの購入です。",
      perCase: "パス",
      free: "無料",
      welcomeBonus: {
        badge: "🎁 新規登録特典",
        title: "新規登録者全員に 3件分（3パス）無料付与",
        body: "無料アカウントを作成すると、初期案件を無料で完了・出力できる3件分の申請パスが即時付与されます。",
      },
      currencyLabel: "表示通貨:",
      tiers: [
        {
          id: "free",
          name: "無料プラン・初期特典",
          price_usd: "$0",
          price_jpy: "¥0",
          unit_usd: "永年無料 · カード不要",
          unit_jpy: "永年無料 · カード登録不要",
          credits: 3,
          badge: "永年無料",
          description: "公表されている審査基準との照合、適格性判定、必要書類チェックリストを無料確認できます。",
          features: [
            "新規登録特典 3件分の無料申請パス（3クレジット）",
            "日本の全対象ビザにおける法定資格チェック",
            "あなた専用の公的提出書類チェックリスト",
            "分岐式ヒアリングによる要件診断",
            "進行状況の保存といつでも再開可能",
            "クレジットカード登録一切不要",
          ],
          cta: "無料で始める（3パス付与）",
        },
        {
          id: "starter",
          name: "1件 申請パス",
          price_usd: "$19",
          price_jpy: "¥2,800",
          unit_usd: "$19 / 件",
          unit_jpy: "¥2,800 / 件",
          credits: 1,
          badge: null,
          description: "1件のビザ申請に必要な全書類（OCR抽出・AI案内・公的PDF一式）の完全作成・出力。",
          features: [
            "申請パス 1件分（1クレジット）",
            "OCRによる書類・在留カードの自動データ抽出",
            "AIによる法定要件・審査基準アドバイス",
            "法務省（出入国在留管理庁）正規様式PDF自動生成",
            "提出前整合性チェック（記載漏れ・矛盾 0件照合）",
            "提出用パッケージ一式（PDF & 編集可能Word）",
          ],
          cta: "1パスを購入 — ¥2,800",
        },
        {
          id: "standard",
          name: "3件 ファミリー・更新パック",
          price_usd: "$39",
          price_jpy: "¥5,800",
          unit_usd: "$13.00 / 件 · 32%お得",
          unit_jpy: "1件あたり¥1,930 · 32%お得",
          credits: 3,
          badge: "人気 · 32%割引",
          description: "配偶者・扶養家族の同時申請、在留期間更新、複数カテゴリの準備に最適です。",
          features: [
            "申請パス 3件分（3クレジット）",
            "1件パスの全機能を含む",
            "配偶者・家族滞在の同時作成対応",
            "所属機関（企業情報）プロファイルの再利用",
            "優先整合性審査エンジン",
            "単品購入より¥2,600お得（32%割引）",
          ],
          cta: "3パスを購入 — ¥5,800",
        },
        {
          id: "family",
          name: "5件 法人・複数申請パック",
          price_usd: "$59",
          price_jpy: "¥8,900",
          unit_usd: "$11.80 / 件 · 38%お得",
          unit_jpy: "1件あたり¥1,780 · 38%お得",
          badge: "最大割引 · 38%お得",
          description: "企業スポンサー、人事担当者、行政書士・代理申請、複数年管理向けパッケージ。",
          features: [
            "申請パス 5件分（5クレジット）",
            "3件パックの全機能を含む",
            "所属機関等作成用（カテゴリー1〜4）一括マッピング",
            "複数年の在留期限・更新トラッキング",
            "法人・チーム向け一括出力・管理",
            "単品購入より¥5,100お得（38%割引）",
          ],
          cta: "5パスを購入 — ¥8,900",
        },
      ],
      footnote:
        "表示価格は1回限りの買い切り価格であり、月額サブスクリプションではありません。1クレジット＝1件のビザ申請完全パスです。新規登録時に3パスが付与されます。法務省・出入国在留管理庁の2026年最新書式仕様に完全対応。",
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
      title: "日本のビザ手続きを、今すぐスムーズに。",
      body: "わずか2分で適格性を確認できます。無料アカウントを作成すると、3件分の無料申請パスを今すぐプレゼント。クレジットカード登録は不要です。",
      cta: "無料で始める — 3パス付き",
    },
    faq: {
      titleBefore: "疑問に、",
      titleAccent: "率直に",
      help: {
        title: "まだ検討中ですか？",
        body: "出典の仕組みと、日本での申請が実際に遅れる原因については、ブログで詳しく解説しています。",
        cta: "記事を読む",
      },
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
            "現在は日本です。就労（技術・人文知識・国際業務）、留学、短期滞在（観光・知人訪問）、家族滞在、日本人・永住者の配偶者等に対応し、新規申請・更新・在留資格変更のいずれも扱えます。Toriiは一度に何か国も広げず、一つずつ完成させてから公開しています。他の国も準備中です。",
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
      cta: "無料で始める — 3パス付き",
      tagline: "日本のビザ申請をガイドします。すべての案内に、規則を公表している当局の出典が付きます。",
      createAccount: "アカウント作成",
      groups: {
        product: "プロダクト",
        routes: "対応ビザ",
        resources: "参考情報",
      },
      disclaimer:
        "Toriiは開発中のプロジェクト名です。申請書類準備のガイドであり、法律相談ではありません。すべての案内には、根拠となる公式の政府ページの出典が付きます。",
    },
  },
};

export type Dictionary = typeof dictionary.en;
