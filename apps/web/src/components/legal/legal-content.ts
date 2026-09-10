export interface LegalSection {
  id: string;
  title: string;
  content: string[];
  subsections?: {
    title: string;
    items: string[];
  }[];
  callout?: {
    type: "info" | "warning" | "shield";
    title: string;
    text: string;
  };
}

export interface LegalDocument {
  title: string;
  badge: string;
  lastUpdated: string;
  summary: string;
  disclaimer?: string;
  sections: LegalSection[];
}

export type PolicyKey = "privacy" | "terms" | "refund" | "cookies";

export const LEGAL_DOCUMENTS: Record<PolicyKey, Record<"en" | "ja", LegalDocument>> = {
  privacy: {
    en: {
      title: "Privacy Policy",
      badge: "Data Protection & APPI / GDPR Compliance",
      lastUpdated: "September 2026",
      summary:
        "At Torii, we understand that immigration documents contain some of your most sensitive personal information — including passport details, residence history, family relationships, tax documents, and employment contracts. This Privacy Policy details how we collect, handle, store, and safeguard your data, and how you retain total control over your documents at all times.",
      disclaimer:
        "Your private immigration documents and case responses are never used to train public machine learning models. Uploaded files are strictly encrypted at rest and in transit.",
      sections: [
        {
          id: "information-collected",
          title: "1. Information We Collect",
          content: [
            "We only collect information necessary to assess your Japanese immigration eligibility, complete official statutory forms, assemble customized required document checklists, and generate personal statements.",
          ],
          subsections: [
            {
              title: "A. Personal Identification & Immigration History",
              items: [
                "Full legal name, nationality, date of birth, sex, and marital status.",
                "Passport number, issue date, expiration date, and issuing authority.",
                "Residence Card (在留カード) number, current Status of Residence, expiration date, and designated activities.",
                "Historical entries into Japan, previous visa applications, and Certificate of Eligibility (CoE) numbers.",
              ],
            },
            {
              title: "B. Employment, Educational & Sponsor Information",
              items: [
                "Japanese employer details: corporate number (法人番号), company name, capital, annual withholding tax category (Category 1 to 4).",
                "Job title, job duties, proposed annual compensation, and employment contract details.",
                "Educational background: degrees, graduation dates, institutions, and Japanese language test scores (e.g., JLPT).",
              ],
            },
            {
              title: "C. Financial & Statutory Evidentiary Records",
              items: [
                "Municipal tax certificates (住民税の課税証明書・納税証明書) and withholding slips (源泉徴収票).",
                "Bank statements or balance certificates required to prove financial solvency for student, dependent, or designated activities visas.",
              ],
            },
            {
              title: "D. Technical & Usage Data",
              items: [
                "Account email address, login timestamps, IP address, device type, browser information, and session tokens.",
              ],
            },
          ],
        },
        {
          id: "how-we-use-information",
          title: "2. How We Use Your Information",
          content: [
            "We use your information strictly to provide and maintain the Torii software platform. Specifically, your data is processed for:",
            "• Form Population: Accurately mapping your questionnaire answers into official statutory Ministry of Justice (法務省) and Immigration Services Agency (出入国在留管理庁) PDF and Excel templates.",
            "• Statutory Checklist Generation: Matching your specific visa category, category tier, and applicant status against published immigration requirements to construct an itemized checklist.",
            "• Inconsistency Detection: Flagging discrepancies (e.g., salary mismatches, date gaps, or missing statutory proofs) before you file.",
            "• Case Resumption: Saving your questionnaire progress across sessions so you can pause and resume filing at any stage.",
            "• Optional Professional Escalation: If you explicitly request professional escalation to a licensed administrative scrivener (行政書士) or immigration lawyer, we share case documents only with your affirmative consent.",
          ],
          callout: {
            type: "shield",
            title: "Zero Model Training on Customer Files",
            text: "Torii does NOT use your uploaded identification documents, tax records, or case answers to train public artificial intelligence models. Any automated extraction or assisted drafting processes operate under strict zero-retention enterprise terms.",
          },
        },
        {
          id: "security-storage",
          title: "3. Security & Storage Architecture",
          content: [
            "We adhere to strict data protection principles designed for high-security legal and compliance workloads:",
            "• Encryption in Transit: All data transmitted between your browser and our servers is encrypted using modern TLS 1.3 protocols.",
            "• Encryption at Rest: User documents and database records are encrypted using industry-standard AES-256 encryption.",
            "• Strict Access Controls: Torii employees have zero access to your uploaded documents and private case responses, except where you explicitly authorize customer support intervention to troubleshoot a technical issue.",
            "• Data Residency & Redundancy: Primary data storage is maintained in enterprise-grade ISO 27001 and SOC 2 Type II certified cloud data centers.",
          ],
        },
        {
          id: "third-party-sharing",
          title: "4. Third-Party Service Providers",
          content: [
            "Torii does not sell, rent, or trade your personal information to advertisers or brokers. We only share information with reputable infrastructure partners under strict data processing agreements:",
            "• Cloud & Database Hosting: Secure hosting providers that manage encrypted infrastructure.",
            "• Payment Processing: Stripe handles payment and credit purchases. Torii never receives or stores your full credit card number or CVV.",
            "• Transactional Email: Providers used solely to send account verifications, password resets, and case status notifications.",
            "• Legal Compliance: We may disclose data only if required by a valid, legally binding order issued by a court of competent jurisdiction under Japanese law.",
          ],
        },
        {
          id: "user-rights",
          title: "5. Your Rights and Data Ownership",
          content: [
            "Under Japan's Act on the Protection of Personal Information (APPI / 個人情報保護法) and global privacy standards (such as GDPR), you retain full rights over your data:",
            "• Right to Access & Export: You can download your generated forms, checklist data, and personal dossier at any time through your dashboard.",
            "• Right to Rectification: You can edit and correct your answers at any point prior to final export.",
            "• Right to Erasure (Deletion): You can delete individual cases or permanently close your account. When you delete a case or account, all uploaded documents, drafted statements, and personal answers are irreversibly purged from our active databases.",
          ],
        },
        {
          id: "contact",
          title: "6. Contact Us",
          content: [
            "If you have questions about this Privacy Policy, your personal data, or wish to exercise your data rights, please contact our Data Protection Team at privacy@torii.jp.",
          ],
        },
      ],
    },
    ja: {
      title: "プライバシーポリシー",
      badge: "個人情報保護法 (APPI) 準拠・セキュリティ方針",
      lastUpdated: "2026年9月",
      summary:
        "Torii（以下「当社」または「本サービス」）は、ビザ申請や在留資格関連の手続きにおいて、旅券（パスポート）番号、在留カード番号、課税・納税証明書、雇用契約書などの極めて機密性の高い個人情報を取り扱うことを深く認識しています。本プライバシーポリシーでは、個人情報保護法に基づき、ユーザーの情報をどのように収集、利用、保管、保護しているかについて説明します。",
      disclaimer:
        "お客様がアップロードした証明書類やケース回答内容は、公開AIモデルのトレーニングに利用されることは一切ありません。すべての通信および保存データは暗号化されています。",
      sections: [
        {
          id: "information-collected",
          title: "1. 収集する情報",
          content: [
            "当社は、日本の出入国在留管理庁（入管）の基準に基づく適格性の確認、法定申請書類の自動作成、必要書類チェックリストの提示に必要な情報のみを収集します。",
          ],
          subsections: [
            {
              title: "A. 本人確認および在留歴に関する情報",
              items: [
                "氏名（アルファベット・漢字・カナ）、国籍・地域、生年月日、性別、婚姻状況。",
                "旅券（パスポート）番号、発行年月日、有効期限、発行機関。",
                "在留カード番号、現在の在留資格、在留期限、指定書の内容。",
                "過去の出入国歴、過去の在留資格申請歴、在留資格認定証明書（CoE）番号。",
              ],
            },
            {
              title: "B. 勤務先・所属機関および学歴に関する情報",
              items: [
                "所属機関（受入企業等）の名称、法人番号、資本金、従業員数、法定調書合計表の提出区分（カテゴリー1〜4）。",
                "職種、担当業務内容、予定給与額、雇用契約期間。",
                "最終学歴（学位、卒業校、専攻）、日本語能力試験（JLPT等）の合格歴。",
              ],
            },
            {
              title: "C. 収入・課税証明および立証資料",
              items: [
                "市区町村発行の住民税の課税証明書・納税証明書、給与所得の源泉徴収票。",
                "留学・家族滞在・特定活動ビザ等で必要となる預貯金残高証明書または経費支弁書関連情報。",
              ],
            },
            {
              title: "D. システム利用情報",
              items: [
                "アカウント登録メールアドレス、アクセス日時、IPアドレス、ブラウザ情報、端末種別、セッショントークン。",
              ],
            },
          ],
        },
        {
          id: "how-we-use-information",
          title: "2. 個人情報の利用目的",
          content: [
            "当社は、収集した個人情報を以下の目的の範囲内でのみ利用します：",
            "• 法定申請書の作成：回答いただいた内容に基づき、法務省・出入国在留管理庁が指定する正式な申請書様式（PDF/Excel）に正確に転記・生成するため。",
            "• 必要書類チェックリストの個別最適化：申請者の状況および所属機関カテゴリーに応じた法定立証書類チェックリストを作成するため。",
            "• 書類の整合性チェック：申請前の日付の齟齬、給与額や業務内容の不整合リスクを自動検知してユーザーに通知するため。",
            "• 進行状況の保存・再開：回答内容を段階的に安全に保存し、いつでも途中から再開できるようにするため。",
            "• 専門家連携（ユーザーの明示的同意がある場合のみ）：行政書士や弁護士へのエスカレーション支援をユーザー自身が依頼した場合に限り、同意を得た範囲でケース情報を共有するため。",
          ],
          callout: {
            type: "shield",
            title: "公開モデルへの学習利用ゼロの誓約",
            text: "Toriiは、お客様の個人データ、回答内容、添付書類を公開AIモデルのトレーニングに利用することは一切ありません。自動書類処理は、データ非保持契約を結んだ安全な環境で行われます。",
          },
        },
        {
          id: "security-storage",
          title: "3. 安全管理措置および暗号化",
          content: [
            "当社は、個人情報保護法に基づく厳格な安全管理措置を講じています：",
            "• 通信の暗号化：すべての通信は最新のTLS 1.3プロトコルによりエンドツーエンドで暗号化されます。",
            "• 保存データの暗号化：データベースおよび保存ファイルは、業界最高水準のAES-256暗号化によって保護されています。",
            "• アクセス制限：当社従業員であっても、ユーザーの個別の申請書類内容を閲覧することはできません（技術サポートの明示的依頼がある場合を除く）。",
            "• 国際基準のクラウド基盤：ISO 27001およびSOC 2認証を取得したデータセンターで保管・運用されています。",
          ],
        },
        {
          id: "third-party-sharing",
          title: "4. 第三者提供について",
          content: [
            "当社は、ユーザーの同意を得ることなく、第三者に個人情報を提供・販売・共有することはありません。ただし、以下の委託先および法的要求を除きます：",
            "• 決済代行：決済処理（Stripe）。当社がクレジットカード番号やセキュリティコードを自社サーバーで保持することはありません。",
            "• インフラ委託先：秘密保持契約およびデータ処理契約を締結したクラウド基盤提供事業者。",
            "• 法令に基づく開示：日本の裁判所の令状や法令の定めに基づく正当な開示請求がある場合。",
          ],
        },
        {
          id: "user-rights",
          title: "5. ユーザーの権利（開示・訂正・削除）",
          content: [
            "個人情報保護法に基づき、ユーザーは以下の権利を行使できます：",
            "• データの確認・ダウンロード：いつでもダッシュボードから入力データおよび生成された申請書類をエクスポートできます。",
            "• データの訂正：申請手続きの完了前であれば、いつでも登録内容を修正できます。",
            "• データの完全消去：ケースの削除またはアカウントの解約を行うことで、保存されたファイルおよび回答データはサーバーから不可逆的に完全消去されます。",
          ],
        },
        {
          id: "contact",
          title: "6. お問い合わせ窓口",
          content: [
            "個人情報の取り扱いに関するご質問、開示請求、苦情のお申し出については、個人情報保護窓口（privacy@torii.jp）までご連絡ください。",
          ],
        },
      ],
    },
  },
  terms: {
    en: {
      title: "Terms of Service",
      badge: "Platform Terms & Legal Disclaimer",
      lastUpdated: "September 2026",
      summary:
        "These Terms of Service govern your access to and use of the Torii web application, document tools, and related services. By registering an account, purchasing filing passes, or generating application materials, you acknowledge and agree to these terms in full.",
      disclaimer:
        "IMPORTANT LEGAL NOTICE: Torii is a guided form-preparation software platform. Torii is not an immigration law firm, does not act as an administrative scrivener (行政書士) or attorney-at-law (弁護士), and does not provide legal advice or official counter representation before the Immigration Services Agency of Japan.",
      sections: [
        {
          id: "nature-of-service",
          title: "1. Nature of the Service",
          content: [
            "Torii provides self-guided software tools designed to help foreign nationals and host companies prepare Japanese immigration forms. Our questionnaire logic and checklists are derived directly from published statutory guidelines of the Ministry of Justice and Immigration Services Agency of Japan (出入国在留管理庁).",
            "Torii automates document formatting, calculates required attachments based on published criteria, and validates internal consistency. The user remains solely responsible for reviewing, signing, and lodging their application with the competent Regional Immigration Bureau (出入国在留管理局).",
          ],
          callout: {
            type: "warning",
            title: "No Legal Representation or Attorney-Client Relationship",
            text: "Use of Torii does not create an attorney-client or administrative scrivener representation agreement. If your case involves complex legal issues, prior deportation or denial history, criminal records, or special discretionary petitions (在留特別許可), you should consult a licensed legal professional.",
          },
        },
        {
          id: "no-guarantee-of-outcomes",
          title: "2. No Guarantee of Immigration Decisions",
          content: [
            "The issuance of a Certificate of Eligibility (CoE), grant of change of status of residence (在留資格変更), extension of period of stay (在留期間更新), or permanent residence permission is at the sole sovereign discretion of the Minister of Justice and Regional Immigration Bureaus of Japan.",
            "Torii makes no warranty or representation that your application will be approved, approved within a specific timeframe, or granted with any particular period of stay (e.g., 1, 3, or 5 years).",
          ],
        },
        {
          id: "user-responsibilities",
          title: "3. User Responsibilities & Statutory Truthfulness",
          content: [
            "By using Torii, you warrant and agree that:",
            "• Accuracy: All information, dates, financial sums, and biographical answers entered into Torii are true, correct, and complete to the best of your knowledge.",
            "• Anti-Fraud Obligation: You will not use Torii to generate fraudulent documents, counterfeit employment records, or sham marriage or adoption papers. Knowingly filing false statements with Japanese immigration authorities carries severe criminal penalties and mandatory deportation under the Immigration Control and Refugee Recognition Act (出入国管理及び難民認定法).",
            "• Final Verification: You will thoroughly inspect all generated documents and attachments before signing and submitting them to the government.",
          ],
        },
        {
          id: "passes-billing",
          title: "4. Passes, Credits & Account Billing",
          content: [
            "• Per-Case Pass Model: Torii operates primarily on a per-case filing pass system (one credit = one complete visa filing package), rather than a recurring subscription.",
            "• Starter Passes: New registered accounts receive complimentary filing passes to evaluate the software.",
            "• Account Security: You are responsible for safeguarding your login credentials and for all activities that occur under your account.",
            "• Inactivity: We do not expire purchased filing credits while your account remains in active, good standing.",
          ],
        },
        {
          id: "intellectual-property",
          title: "5. Intellectual Property",
          content: [
            "The Torii application, design systems, proprietary rules engine, questionnaire logic, code, and brand marks are the exclusive intellectual property of Torii and its licensors. Official statutory form layouts and government text remain the property of their respective government authorities.",
          ],
        },
        {
          id: "limitation-of-liability",
          title: "6. Limitation of Liability",
          content: [
            "To the maximum extent permitted by applicable law, Torii and its creators shall not be liable for any indirect, incidental, punitive, or consequential damages, including loss of profits, visa denial costs, travel disruption, or loss of legal status.",
            "Torii's total cumulative liability for any claim arising out of or related to these Terms or the service shall not exceed the amount actually paid by you to Torii for the filing pass directly giving rise to the claim.",
          ],
        },
        {
          id: "governing-law",
          title: "7. Governing Law & Jurisdiction",
          content: [
            "These Terms and any disputes arising out of your use of Torii shall be governed by and construed in accordance with the laws of Japan, without regard to its conflict of law provisions. The Tokyo District Court shall have exclusive jurisdiction as the court of first instance.",
          ],
        },
      ],
    },
    ja: {
      title: "利用規約",
      badge: "サービス利用規約・免責事項",
      lastUpdated: "2026年9月",
      summary:
        "本利用規約（以下「本規約」）は、Torii（以下「本サービス」）の利用条件を定めるものです。アカウント登録、申請パスの購入、または申請書類の作成を行った時点で、本規約のすべての内容に同意したものとみなされます。",
      disclaimer:
        "【重要事項・非弁行為の排除に関する告知】Toriiは、ビザ申請書類の作成を補助するセルフガイド型のソフトウェアツールです。本サービスは法律事務所ではなく、行政書士法または弁護士法に基づく代理業務・法律相談を行うものではありません。出入国在留管理局に対する申請代理や個別法的判断を提供するものではありません。",
      sections: [
        {
          id: "nature-of-service",
          title: "1. サービスの本質と提供範囲",
          content: [
            "Toriiは、日本での在留資格申請（就労・留学・家族滞在・永住等）を行う個人および受入機関のために、出入国在留管理庁が公表している法令・ガイドラインに準拠した書類作成支援ソフトウェアを提供します。",
            "ユーザーが入力した情報をもとに法定様式の書類作成および必要書類チェックリストの整理を自動化しますが、完成した書類の確認、署名、および地方出入国在留管理局への提出はユーザー自身の責任において行われます。",
          ],
          callout: {
            type: "warning",
            title: "弁護士・行政書士の代理業務との区別",
            text: "本サービスの利用により、ユーザーと当社との間に委任契約や代理権が発生することはありません。不許可歴、犯罪歴、退去強制歴、または在留特別許可などの個別かつ高度な法的判断を要する場合は、有資格の行政書士または弁護士にご相談ください。",
          },
        },
        {
          id: "no-guarantee-of-outcomes",
          title: "2. 審査結果および在留許可の非保証",
          content: [
            "在留資格認定証明書（CoE）の交付、在留資格変更許可、在留期間更新許可などの許認可の可否は、法務大臣および地方出入国在留管理局の裁量に委ねられています。",
            "Toriiは、申請の許可、審査期間の短縮、または希望する在留期間（1年・3年・5年等）の付与について、一切の保証を行うものではありません。",
          ],
        },
        {
          id: "user-responsibilities",
          title: "3. ユーザーの義務および申告の真実性",
          content: [
            "ユーザーは、本サービスを利用するにあたり以下の事項を遵守するものとします：",
            "• 真実の申告：入力する個人情報、職歴、学歴、収入、および滞在実績がすべて真実かつ最新であることを保証すること。",
            "• 偽装申請の禁止：偽造書類の作成、虚偽の雇用証明、偽装結婚その他不正な手段による在留資格取得の目的に本サービスを利用してはなりません。虚偽の申請は出入国管理及び難民認定法違反（不法就労助長・虚偽申告）として刑事処罰および退去強制の対象となります。",
            "• 最終書類の自己確認：印刷・提出前に、生成されたすべての書類の内容をご自身で入念に点検し、納得の上で署名・提出すること。",
          ],
        },
        {
          id: "passes-billing",
          title: "4. パス（クレジット）および料金体系",
          content: [
            "• 買い切り型クレジット制度：Toriiは月額自動更新サブスクリプションではなく、1件の完全な申請書類一式につき1パスを消費する買い切り型システムを採用しています。",
            "• 無料パス：新規登録ユーザーには、サービスの適合性を確認するための無料申請パスが付与されます。",
            "• アカウント管理：アカウント情報の適切な管理はユーザーの責任とし、第三者へのアカウント譲渡・貸与を禁じます。",
            "• クレジットの有効期間：有効なアカウントである限り、購入されたクレジットは失効しません。",
          ],
        },
        {
          id: "intellectual-property",
          title: "5. 知的財産権",
          content: [
            "Toriiを構成するプログラム、アルゴリズム、UIデザイン、独自チェックロジック、および商標に関する知的財産権は当社に帰属します。政府が公表する公式法定様式の著作権は関係官庁の定めに従います。",
          ],
        },
        {
          id: "limitation-of-liability",
          title: "6. 免責および責任の制限",
          content: [
            "当社は、本サービスに関連してユーザーに生じた間接損害、特別損害、ビザ不許可による損害、航空券や渡航費用の損失について、法令で許容される最大限の範囲において一切の責任を負いません。",
            "当社がユーザーに対して負う損害賠償責任の総額は、当該損害の原因となった申請パスに関してユーザーが当社に実際に支払った金額を上限とします。",
          ],
        },
        {
          id: "governing-law",
          title: "7. 準拠法および合意管轄",
          content: [
            "本規約の解釈および適用は日本法に準拠するものとします。本サービスに関連して生じた一切の紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とします。",
          ],
        },
      ],
    },
  },
  refund: {
    en: {
      title: "Refund Policy",
      badge: "Transparent 30-Day Guarantee",
      lastUpdated: "September 2026",
      summary:
        "We want you to feel completely confident using Torii. Because we charge on a transparent, per-case credit basis rather than locking you into recurring monthly subscriptions, our refund terms are simple, fair, and straightforward.",
      disclaimer:
        "All unused case credits purchased within the last 30 days are fully refundable upon request.",
      sections: [
        {
          id: "credit-system",
          title: "1. How Credits & Billing Work",
          content: [
            "• Pay-As-You-Go: Torii does not charge recurring monthly or annual subscription fees. You only purchase passes when you need them.",
            "• 1 Pass = 1 Case Packet: A pass entitles you to unlimited revisions, form re-exports, checklist regenerations, and validation checks for that specific application case.",
            "• 3 Free Starter Passes: New users receive 3 free passes upon signing up. Free passes carry no monetary value and are not eligible for cash refunds.",
          ],
        },
        {
          id: "unused-credits-refund",
          title: "2. 30-Day Money-Back Guarantee for Unused Passes",
          content: [
            "If you purchased case credits and have not used them to generate or export a completed application packet, you may request a 100% refund within 30 days of the purchase date.",
            "No questions asked. Once approved, the refund will be credited directly back to the original payment method.",
          ],
        },
        {
          id: "technical-malfunction",
          title: "3. Technical Failure & Generation Malfunctions",
          content: [
            "If a technical bug, system error, or generation defect on Torii's platform prevents your statutory immigration forms from properly populating, formatting, or exporting, and our engineering team cannot resolve the problem within 48 hours of your support ticket, you are entitled to:",
            "• A full monetary refund of the credit used for that case; or",
            "• An immediate free credit replacement to your account balance, at your choice.",
          ],
        },
        {
          id: "non-refundable",
          title: "4. Non-Refundable Circumstances",
          content: [
            "We cannot issue refunds under the following conditions:",
            "• Government Decisions: Visa refusals, denials, issuance delays, or granting of shorter validity periods by the Immigration Services Agency of Japan. Because government outcomes depend entirely on official discretion and applicant eligibility, Torii cannot guarantee or refund based on immigration results.",
            "• Successfully Exported Packets: Cases where the full document package has been successfully generated, downloaded, and reviewed without technical defect.",
            "• Purchases Older Than 30 Days: Credit purchases made more than 30 days prior to the refund request.",
          ],
          callout: {
            type: "info",
            title: "Fair Resolution Commitment",
            text: "If you encounter unusual circumstances or feel your experience did not meet our high standard of quality, please reach out. We review every situation thoughtfully and strive for a fair resolution.",
          },
        },
        {
          id: "requesting-a-refund",
          title: "5. How to Request a Refund",
          content: [
            "To request a refund, simply send an email to support@torii.jp with:",
            "1. Your registered account email address;",
            "2. The Stripe payment receipt or transaction ID;",
            "3. The reason for your request (and case ID if reporting a technical glitch).",
            "Our team will process your request within 2 business days. Approved refunds typically appear on your credit card or original payment statement within 5 to 7 business days depending on your financial institution.",
          ],
        },
      ],
    },
    ja: {
      title: "返金ポリシー",
      badge: "購入後30日間の安心返金保証",
      lastUpdated: "2026年9月",
      summary:
        "Toriiでは、月額自動更新のような不透明なサブスクリプションを排除し、1件ごとの完全な買い切り型クレジット制度を採用しています。安心してご利用いただくため、明確で公正な返金ポリシーを定めています。",
      disclaimer:
        "ご購入から30日以内の未使用申請パス（クレジット）は、理由を問わず全額返金の対象となります。",
      sections: [
        {
          id: "credit-system",
          title: "1. 料金体系とクレジットの仕組み",
          content: [
            "• 完全買い切り制：月額または年額の自動課金は一切ありません。必要なときに必要な分だけパスを購入いただけます。",
            "• 1パス＝1申請分：1クレジットで、その申請ケースに関する修正、再出力、チェックリスト更新、整合性チェックが無制限に行えます。",
            "• 新規登録時の3パス無料付与：新規アカウントには動作確認用の無料パスが3件付与されます。無料パスには金銭的価値はなく、換金や返金の対象外です。",
          ],
        },
        {
          id: "unused-credits-refund",
          title: "2. 未使用クレジットの30日間返金保証",
          content: [
            "ご購入いただいた申請クレジットをまだケースの出力（書類生成）に使用していない場合、購入日から30日以内であれば、理由を問わず100%全額返金を承ります。",
            "返金が承認され次第、ご購入時のお支払い方法（クレジットカード等）を通じて全額が返金されます。",
          ],
        },
        {
          id: "technical-malfunction",
          title: "3. システム障害・出力不具合に対する保証",
          content: [
            "万が一、当社のシステム障害やプログラムの不具合により、法定申請書が正常に作成・ダウンロードできない事象が発生し、サポートへのお問い合わせから48時間以内に解消できない場合は、以下のいずれかの対応を行います：",
            "• 当該ケースに消費されたクレジット代金の全額返金",
            "• または、代替クレジットの即時無償付与",
          ],
        },
        {
          id: "non-refundable",
          title: "4. 返金対象外となるケース",
          content: [
            "以下の場合は返金の対象外となりますのであらかじめご了承ください：",
            "• 入管の審査結果による不許可・遅延：出入国在留管理局による審査結果（不許可、追加書類提出通知、希望より短い在留期間の付与など）を理由とする返金。審査結果は国家機関の専権事項であり、本サービスが保証するものではありません。",
            "• 正常に出力完了した書類一式：システムの不具合なく申請書類一式が正常にダウンロードされ、サービスが完全に提供された場合。",
            "• 購入日から30日を経過したクレジット：ご購入から30日以上が経過した取引。",
          ],
          callout: {
            type: "info",
            title: "誠実なサポートの約束",
            text: "個別のご事情や予期せぬトラブルが生じた場合は、サポート窓口までお気軽にご相談ください。規約に形式的に囚われることなく、誠意を持って柔軟に対応いたします。",
          },
        },
        {
          id: "requesting-a-refund",
          title: "5. 返金のお手続き方法",
          content: [
            "返金をご希望の場合は、以下の情報を記載の上、サポート窓口（support@torii.jp）までメールをお送りください：",
            "1. ご登録のメールアドレス",
            "2. Stripeの決済完了メールまたは領収書番号（Transaction ID）",
            "3. 返金理由（不具合報告の場合はケースID）",
            "原則2営業日以内に確認・手続きを行い、承認後5〜7営業日以内にお客様のカード会社を通じて返金が反映されます。",
          ],
        },
      ],
    },
  },
  cookies: {
    en: {
      title: "Cookie Policy",
      badge: "Cookie Transparency & Local Storage",
      lastUpdated: "September 2026",
      summary:
        "This Cookie Policy explains how Torii uses cookies, web beacons, and browser local storage technologies when you access our application. We use these technologies strictly to keep you authenticated, remember your preferences, and maintain bank-grade security.",
      disclaimer:
        "We do not sell your browsing history to third-party ad brokers or track you across external websites.",
      sections: [
        {
          id: "what-are-cookies",
          title: "1. What Are Cookies and Local Storage?",
          content: [
            "Cookies are small text files placed on your computer or mobile device when you visit websites. Local Storage is a modern browser technology that allows web applications to securely store preferences and session tokens directly on your device without transmitting them across every HTTP request.",
          ],
        },
        {
          id: "cookies-we-use",
          title: "2. Categories of Cookies We Use",
          content: [
            "Torii uses only a minimal set of cookies and storage keys categorized into the following purposes:",
          ],
          subsections: [
            {
              title: "A. Strictly Necessary / Essential Cookies",
              items: [
                "Authentication Tokens (e.g., torii_access_token): Keep you securely logged in as you navigate between intake steps and document review.",
                "CSRF Tokens: Protect against Cross-Site Request Forgery attacks, ensuring that form submissions genuinely originate from your browser.",
                "Load Balancing: Direct your network traffic to healthy server clusters to ensure fast response times.",
              ],
            },
            {
              title: "B. Functional & Preference Cookies",
              items: [
                "Language Selector (torii_lang / torii-landing-lang): Remembers whether you prefer English or Japanese.",
                "Theme Mode (theme / next-theme): Remembers your preference for light mode or dark mode.",
                "UI State: Remembers collapsible sidebar states and checklist drawer positions.",
              ],
            },
            {
              title: "C. Performance & Error Monitoring",
              items: [
                "Privacy-Preserving Telemetry: Anonymized client error logging to detect and fix broken form fields or PDF rendering glitches without collecting personal identifiable information.",
              ],
            },
            {
              title: "D. Third-Party Payment Processing Cookies",
              items: [
                "Stripe Fraud Detection: When you purchase credits via our Stripe checkout integration, Stripe sets essential fraud-prevention cookies (e.g., __stripe_mid, __stripe_sid) to protect against credit card fraud.",
              ],
            },
          ],
        },
        {
          id: "no-tracking-ads",
          title: "3. No Third-Party Advertising Trackers",
          content: [
            "Torii is an immigration document tool, not an ad-supported publication. We do NOT deploy third-party advertising cookies, retargeting pixels (such as Facebook Pixel or ad network beacons), or behavioral profiling trackers.",
          ],
        },
        {
          id: "controlling-cookies",
          title: "4. Managing and Disabling Cookies",
          content: [
            "You have full control over cookies through your web browser settings. Most browsers permit you to:",
            "• View which cookies are stored on your device and delete them individually;",
            "• Block third-party cookies;",
            "• Block cookies from particular websites;",
            "• Block all cookies completely.",
            "Please note: If you disable strictly necessary authentication cookies, you will not be able to log in or save your immigration case progress on Torii.",
          ],
          callout: {
            type: "info",
            title: "Browser Instructions",
            text: "To modify cookie settings, visit your browser's Privacy or Settings panel (in Chrome: chrome://settings/cookies; in Safari: Preferences > Privacy; in Firefox: Settings > Privacy & Security).",
          },
        },
        {
          id: "contact",
          title: "5. Questions About Our Cookie Usage",
          content: [
            "If you have questions about how we use cookies or local storage, please reach out to our privacy engineering team at privacy@torii.jp.",
          ],
        },
      ],
    },
    ja: {
      title: "クッキーポリシー",
      badge: "クッキーおよびローカルストレージの利用方針",
      lastUpdated: "2026年9月",
      summary:
        "本クッキーポリシーは、Torii（以下「本サービス」）において、クッキー（Cookie）およびブラウザのローカルストレージ（Local Storage）等の技術をどのように利用しているかを説明するものです。当社は、ユーザーのログイン状態の維持、言語設定の保持、およびセキュリティ確保のためにこれらの技術を使用しています。",
      disclaimer:
        "当社がユーザーの閲覧履歴を行動ターゲティング広告会社に販売したり、外部サイトにまたがる行動追跡を行うことはありません。",
      sections: [
        {
          id: "what-are-cookies",
          title: "1. クッキーおよびローカルストレージとは",
          content: [
            "クッキーとは、ウェブサイトを閲覧した際にブラウザに保存される小さなテキストファイルです。ローカルストレージは、ブラウザ内に安全にデータを保持し、言語設定や画面表示設定をスムーズに読み込むための最新のブラウザ技術です。",
          ],
        },
        {
          id: "cookies-we-use",
          title: "2. 本サービスで使用するクッキーの種類",
          content: [
            "Toriiで使用するクッキーおよびストレージデータは、以下の必要不可欠な目的に限定されています：",
          ],
          subsections: [
            {
              title: "A. 必須（セキュリティ・認証用）クッキー",
              items: [
                "認証トークン（torii_access_token等）：ケース入力画面やダッシュボード間を移動する際に、安全なログイン状態を維持します。",
                "CSRF対策トークン：クロスサイトリクエストフォージェリ攻撃を防止し、悪意ある偽装通信からユーザーを保護します。",
                "負荷分散（ロードバランサー）：サーバーへのアクセスを適切に分散し、快適な表示速度を確保します。",
              ],
            },
            {
              title: "B. 機能・ユーザー設定用クッキー",
              items: [
                "言語選択（torii_lang / torii-landing-lang）：日本語と英語の表示選択を記憶します。",
                "テーマ設定（theme / next-theme）：ダークモードまたはライトモードの表示設定を記憶します。",
                "画面状態の保持：サイドバーの開閉状態やチェックリストの展開状態を保持します。",
              ],
            },
            {
              title: "C. パフォーマンスおよびエラー監視",
              items: [
                "匿名エラーログ：個人を特定できない形でシステム障害や画面クラッシュを検知し、サービスの品質向上を図るために使用します。",
              ],
            },
            {
              title: "D. 決済代行事業者によるクッキー",
              items: [
                "Stripeの不正防止クッキー：申請クレジットの決済時に、クレジットカードの不正利用を防止するためにStripe社が設定する必須クッキー（__stripe_mid、__stripe_sid等）。",
              ],
            },
          ],
        },
        {
          id: "no-tracking-ads",
          title: "3. 広告追跡クッキーの不使用",
          content: [
            "Toriiは行政手続き書類作成支援ツールであり、広告収入モデルのサイトではありません。第三者の行動ターゲティング広告クッキー、リターゲティング用ピクセル（Meta Pixel等）、および第三者トラッカーは一切設置していません。",
          ],
        },
        {
          id: "controlling-cookies",
          title: "4. クッキーの管理・無効化方法",
          content: [
            "ユーザーは、ブラウザの設定を変更することにより、クッキーの保存を制限または削除することができます：",
            "• 保存されているクッキーの個別確認および削除",
            "• サードパーティ製クッキーのブロック",
            "• すべてのクッキーの一括ブロック",
            "注意：必須クッキー（認証用クッキー）を無効化した場合、ログインや申請ケースの保存などの本サービスの主要機能が正常にご利用いただけなくなります。",
          ],
          callout: {
            type: "info",
            title: "ブラウザ設定手順",
            text: "主要ブラウザのプライバシー設定またはCookie設定画面（Chrome: 設定 > プライバシーとセキュリティ、Safari: 環境設定 > プライバシー）からいつでもクッキーの管理が可能です。",
          },
        },
        {
          id: "contact",
          title: "5. クッキーに関するお問い合わせ",
          content: [
            "本クッキーポリシーに関するご質問は、プライバシー窓口（privacy@torii.jp）までお問い合わせください。",
          ],
        },
      ],
    },
  },
};
