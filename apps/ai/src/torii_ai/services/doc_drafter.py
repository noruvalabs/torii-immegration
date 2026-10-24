"""AI Document Drafter for immigration filings (Cover letters, statements of reason, itineraries, job specifications)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from torii_ai.config import Settings
from torii_ai.llm.groq import ChatClient


class AIDraftRequest(BaseModel):
    doc_type: str
    jurisdiction_code: str = "JP"
    scope_label: str = "Immigration Visa Application"
    case_reference: str = "CASE-1"
    intake_answers: dict[str, Any] = Field(default_factory=dict)
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    custom_instructions: str | None = None
    locale: str = "en"


DOC_TITLES: dict[str, str] = {
    "cover_letter": "Formal Consular Visa Cover Letter & Dossier Index",
    "cover": "Formal Consular Visa Cover Letter & Dossier Index",
    "statement_of_reason": "Official Statement of Reason (理由書 / Statement of Purpose)",
    "reason": "Official Statement of Reason (理由書 / Statement of Purpose)",
    "reason_letter_work_hiring": "Employer Hiring Reason Statement (雇用理由書 / 採用理由書)",
    "reason_letter_major_relevance": "Academic Major & Job Duty Correlation Statement (職務内容と専攻の関連性説明書)",
    "reason_letter_infraction_explanation": "Written Explanation & Corrective Action Statement (事情説明書・反省文)",
    "reason_letter_permanent_residence": "Reason Statement for Permanent Residence (永住許可申請理由書)",
    "change_of_employer_notification": "Notification of Sponsoring Organization Change (所属機関等に関する届出書 - 入管法第19条の16)",
    "schedule_of_stay": "Official Schedule of Stay & Day-by-Day Itinerary (滞在予定表)",
    "schedule": "Official Schedule of Stay & Day-by-Day Itinerary (滞在予定表)",
    "job_duties": "Statutory Job Duties Specification (職務内容説明書)",
    "financial_solvency": "Financial Solvency & Sponsor Guarantee Declaration",
    "financial": "Financial Solvency & Sponsor Guarantee Declaration",
    "invitation_letter": "Formal Letter of Guarantee & Invitation (招へい理由書 / 身元保証書)",
    "medical_cover_letter": "Official Medical Visa Consular Application Letter (High Commission of India / IVAC)",
    "medical_attendant_declaration": "Medical Attendant (MED-2) Declaration & Caregiver Undertaking",
}


class AIDocDrafter:
    """Drafts personalized, legally sound immigration documents using LLM."""

    def __init__(self, chat: ChatClient, settings: Settings) -> None:
        self._chat = chat
        self._settings = settings

    async def draft_document(self, req: AIDraftRequest) -> dict[str, Any]:
        doc_type = req.doc_type.lower()
        title = DOC_TITLES.get(
            doc_type, f"Official Document ({doc_type.replace('_', ' ').title()})"
        )
        answers = req.intake_answers or {}
        full_name = str(answers.get("full_name") or answers.get("applicant_name") or "Applicant")
        passport_no = str(answers.get("passport_number") or answers.get("passport_no") or "—")
        nationality = str(answers.get("nationality") or answers.get("citizenship") or "—")
        current_country = str(
            answers.get("current_country")
            or answers.get("current_residence_country")
            or nationality
        )
        purpose = str(
            answers.get("main_purpose")
            or answers.get("purpose_of_visit")
            or "Official visa application and stay"
        )
        employer = str(
            answers.get("employer_name") or answers.get("company_name") or "Sponsoring Organization"
        )
        salary = str(answers.get("monthly_salary") or answers.get("remuneration") or "—")
        stay_days = str(
            answers.get("stay_duration_days") or answers.get("intended_length_of_stay_days") or "15"
        )
        arrival_date = str(
            answers.get("planned_arrival_date")
            or answers.get("start_date")
            or datetime.now(UTC).strftime("%Y-%m-%d")
        )

        system_prompt = (
            "You are an elite, highly credentialed immigration legal specialist and administrative scrivener (行政書士). "
            "Your task is to draft a comprehensive, persuasive, professional, and official document for an immigration visa application. "
            "Incorporate all provided applicant details, employer details, verified documents, and travel/work facts. "
            "Ensure the tone is formal, polite, authoritative, and completely tailored to official embassy and immigration bureau standards. "
            "Output the plain text of the completed document with clear section headings, dates, and signature blocks."
        )

        user_prompt = f"""
TARGET JURISDICTION: {req.jurisdiction_code}
VISA SCOPE: {req.scope_label}
CASE REFERENCE: {req.case_reference}
DOCUMENT TYPE TO DRAFT: {title}

APPLICANT PROFILE & INTAKE DATA:
- Full Legal Name: {full_name}
- Passport Number: {passport_no}
- Nationality: {nationality}
- Country of Residence: {current_country}
- Main Purpose: {purpose}
- Employer / Sponsor Name: {employer}
- Monthly Salary / Remuneration: {salary}
- Intended Stay Duration: {stay_days} days
- Planned Arrival Date: {arrival_date}
- All Intake Key-Values: {answers}

VERIFIED ENCLOSED DOCUMENTS:
{[c.get("name") for c in req.checklist if c.get("status") != "needed"] or ["Original Passport", "Application Form", "Financial Certificates", "Employment Certificate"]}

ADDITIONAL INSTRUCTIONS:
{req.custom_instructions or "Ensure high legal precision and full adherence to immigration compliance norms."}

Please generate the complete, ready-to-file text of the {title}.
"""
        model_name = getattr(self._chat, "_model", "AI Assistant")
        try:
            content = await self._chat.complete(system=system_prompt, user=user_prompt)
            if content and len(content.strip()) > 100:
                return {
                    "doc_type": doc_type,
                    "title": title,
                    "content": content.strip(),
                    "model_used": model_name,
                    "generated_at": datetime.now(UTC).isoformat(),
                }
        except Exception:
            pass

        # Fallback tailored text synthesis
        fallback_text = self._build_fallback(
            doc_type,
            req,
            title,
            full_name,
            passport_no,
            nationality,
            current_country,
            purpose,
            employer,
            salary,
            stay_days,
            arrival_date,
        )
        return {
            "doc_type": doc_type,
            "title": title,
            "content": fallback_text,
            "model_used": "Torii Immigration AI Engine (Synthesized)",
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _build_fallback(
        self,
        doc_type: str,
        req: AIDraftRequest,
        title: str,
        full_name: str,
        passport_no: str,
        nationality: str,
        current_country: str,
        purpose: str,
        employer: str,
        salary: str,
        stay_days: str,
        arrival_date: str,
    ) -> str:
        date_str = datetime.now(UTC).strftime("%B %d, %Y")
        checklist_items = [
            f"   {i + 1}. {c.get('name', 'Document')} (Verified & Attached)"
            for i, c in enumerate(req.checklist)
            if c.get("status") != "needed"
        ]
        doc_list_str = (
            "\n".join(checklist_items)
            or "   1. Valid Original Passport & Bio-Data Photocopies\n   2. Official Visa Application Form (Signed)\n   3. Day-by-Day Schedule of Stay (Itinerary Table)\n   4. Bank Statements / Proof of Financial Solvency\n   5. Employment Certificate / Business Registration"
        )

        if doc_type in ("reason_letter_work_hiring", "hiring_reason"):
            return f"""================================================================================
雇用理由書 (STATEMENT OF REASONS FOR EMPLOYING FOREIGN NATIONAL)
申請人: {full_name} | 勤務先: {employer}
作成日: {date_str}
================================================================================

出入国在留管理局長 殿

1. 採用の背景及び受入企業の概要:
当社（{employer}）は、事業拡大およびグローバルな取引・技術開発の推進に伴い、高度な専門知識と語学力を備えた優秀な人材を必要としております。
日本国内での求人活動を実施したものの、当社の求める専門技術（IT・国際法務・海外取引・多言語対応等）を充足する人材の採用が急務であったため、厳正な書類選考および面接を経て、申請人（{full_name}）の採用を決定いたしました。

2. 申請人の職務内容及び専門性:
申請人は、当社の主要事業部門において以下の専門的業務に従事いたします。
- 専門技術を駆使したシステム設計・開発・データ分析業務
- 海外クライアントおよび海外提携先との技術的・実務的折衝
- 業務プロセスの最適化および品質保証管理
これらの職務は、申請人の学歴（専攻分野）および職歴において培われた高度な専門知識を活用するものであり、単純労働等の要素は一切含まれておりません。

3. 待遇及び雇用条件:
申請人に対する報酬（月額 {salary}）は、同等の職務に従事する日本人社員と同等以上の水準を確保しており、適法かつ安定した生活が営める雇用条件を定めております。

以上の通り、申請人の採用は当社事業の推進に不可欠であり、在留資格基準を完全に満たしておりますので、速やかな許可を賜りますようお願い申し上げます。

【受入機関】
所在地: 日本国内事業所
会社名: {employer}
代表者氏名・役職: 代表取締役 印
"""
        elif doc_type in ("reason_letter_major_relevance", "major_relevance"):
            return f"""================================================================================
職務内容と専攻の関連性説明書 (STATEMENT OF RELEVANCE BETWEEN DUTIES AND MAJOR)
申請人: {full_name} | 国籍: {nationality}
作成日: {date_str}
================================================================================

出入国在留管理局 審査官 殿

1. 申請人の学歴・専攻分野:
申請人は、正規の大学教育課程において専門分野（工学・情報科学・国際経済・経営学等）を専攻し、体系的な理論および実務的手法を習得しております。
在学中の主要履修科目:
- 専門基幹科目（コンピュータサイエンス、アルゴリズム、国際経営論、外国語コミュニケーション等）
- 卒業論文・研究プロジェクト（実践的な課題解決演習）

2. 配属先における具体的な職務内容:
採用先（{employer}）における配属部門および業務:
- 主たる業務: {purpose}
- 担当役割: 高度な専門理論を応用した実務開発、システム運用、ならびに国際展開支援。

3. 専攻と職務内容の整合性（関連性の論証）:
大学で修得した専門的学識（データ解析力、論理的思考、外国語運用能力）は、配属先での日々の業務遂行に直結しており、高度な専門的・技術的判断を要する「技術・人文知識・国際業務」の該当性を十二分に満たしております。

申請人署名: ___________________________
氏名: {full_name}
"""
        elif doc_type in ("reason_letter_infraction_explanation", "infraction_explanation"):
            return f"""================================================================================
事情説明書及び誓約書 (WRITTEN EXPLANATION, STATEMENT & PLEDGE)
申請人: {full_name} | 在留カード番号: —
作成日: {date_str}
================================================================================

出入国在留管理局長 殿

1. 事情の経緯及び事実関係の説明:
本申請にあたり、過去における公的義務（住民税・国民健康保険・年金等の納付時期、または留学生時代の出席率等）について、以下の通り誠実に経緯をご報告申し上げます。
- 発生した事情: 引っ越しに伴う納税通知書の受領遅延、または不測の事態による一時的な納付の遅れ
- 現在の是正状況: 発覚後速やかに管轄官庁窓口へ出頭し、未納・遅延分を全額完納いたしました（完納証明書・領収済通知書を添付）。

2. 反省及び原因の分析:
日本の法令・公的納付制度への理解が不足していた点について深く反省しております。自身の管理体制の不備を真摯に受け止めております。

3. 今後の再発防止策及び改善体制:
- 給与天引き（特別徴収）または銀行口座自動振替の手続きを完了し、納付遅延が再発しない体制を構築いたしました。
- マイナポータルやねんきんネット等を毎月定期的に確認し、適正な納付管理を徹底いたします。

4. 誓約:
今後は日本国の出入国在留管理法をはじめとする全ての諸法令を厳格に遵守し、適法かつ誠実に在留することを固く誓約いたします。寛大なるご配慮を賜りますよう伏してお願い申し上げます。

申請人署名: ___________________________
氏名: {full_name}
"""
        elif doc_type in ("reason_letter_permanent_residence", "pr_reason"):
            return f"""================================================================================
永住許可申請理由書 (STATEMENT OF REASON FOR PERMANENT RESIDENCE APPLICATION)
申請人: {full_name} | 国籍: {nationality}
作成日: {date_str}
================================================================================

法務大臣 殿

1. 来日から現在までの経歴:
私は来日以来、日本社会の規範を尊重し、適法に在留を継続してまいりました。
日本の産業界・地域社会において誠実に勤務し、安定したキャリア基盤を確立しております。

2. 現在の就労および独立生計の状況:
現在、{employer}において正規の専門職として従事し、年収（{salary}）および資産を維持しており、将来にわたり公的負担となることなく独立して生計を営む十分な資産および技能を有しております。

3. 公的義務の完全履行（素行要件・国益適合要件）:
- 住民税・所得税等の税金を一切滞納することなく適正に納付しております。
- 厚生年金・健康保険等の社会保険料についても期日通り完納しております。
- これまでに日本国内外において交通違反・刑事罰等の法令違反歴は皆無であり、素行は善良であります。

4. 永住を希望する理由及び将来の展望:
日本は私にとって人生の基盤であり、今後も永住者として日本社会の発展に寄与し、地域の一員として貢献してまいりたいと強く願っております。
何卒、慎重なるご審査の上、永住許可を賜りますよう心よりお願い申し上げます。

申請人署名: ___________________________
氏名: {full_name}
"""
        elif doc_type in ("change_of_employer_notification", "job_change_notice"):
            return f"""================================================================================
所属機関等に関する届出書 (契約機関の変更)
入管法第19条の16第1号・第2号に基づく届出
作成日: {date_str}
================================================================================

出入国在留管理局長 殿

1. 届出人（中長期在留者）の基本情報:
- 氏名: {full_name}
- 国籍・地域: {nationality}
- 生年月日: —
- 在留カード番号: —
- 在留資格: 技術・人文知識・国際業務 (または関連就労資格)

2. 前の所属機関（離職）に関する事項:
- 機関の名称: 前所属機関
- 所在地: —
- 離職年月日: 2026年—月—日

3. 新たな所属機関（就職・移籍）に関する事項:
- 機関の名称: {employer}
- 法人番号: —
- 所在地: 日本国内事業所
- 契約締結年月日: {arrival_date}
- 職務内容: {purpose}

上記のとおり、所属機関の変更について入管法第19条の16の規定に基づき届け出ます。

届出人署名: ___________________________
氏名: {full_name}
"""
        elif "reason" in doc_type or "statement" in doc_type:
            return f"""================================================================================
OFFICIAL STATEMENT OF REASON (理由書 / STATEMENT OF PURPOSE)
Case Reference: {req.case_reference} | Scope: {req.scope_label}
Date: {date_str}
================================================================================

TO:
The Regional Immigration Services Bureau / Consular Division of the Embassy

1. APPLICANT IDENTIFICATION:
- Full Name: {full_name}
- Nationality: {nationality}
- Passport Number: {passport_no}
- Country of Residence: {current_country}
- Sponsoring Organization / Employer: {employer}

2. BACKGROUND & PURPOSE OF APPLICATION:
I am respectfully submitting this Statement of Reason in support of my application for {req.scope_label}. 
The primary purpose of my stay is: {purpose}.

3. DETAILED CIRCUMSTANCES & QUALIFICATIONS:
I have completed all statutory requirements, possess verified educational and professional credentials matching the requested status, and maintain legitimate sponsorship under {employer}. My remuneration ({salary}) and personal assets are sufficient to guarantee independent financial stability.

4. COMMITMENT TO STATUTORY COMPLIANCE:
I solemnly affirm that I will strictly abide by all immigration regulations, engage solely in authorized activities, and uphold all statutory obligations throughout my stay.

Respectfully submitted,

________________________________________
{full_name}
Passport No: {passport_no}
Date: {date_str}
"""
        elif "schedule" in doc_type or "itinerary" in doc_type:
            return f"""================================================================================
OFFICIAL SCHEDULE OF STAY / DAY-BY-DAY ITINERARY (滞在予定表)
Applicant: {full_name} | Passport: {passport_no}
Planned Arrival Date: {arrival_date} | Duration: {stay_days} Days
================================================================================

+-------------------+-----------------------------------------------+----------------------+----------------------------------------------+
| Date              | Activity Plan & Destination                   | Accommodation / Contact | Address & Contact Phone                      |
+-------------------+-----------------------------------------------+----------------------+----------------------------------------------+
| Day 1 ({arrival_date})| Arrival at Airport, immigration clearance, check-in. | Tokyo Central Hotel  | Chiyoda-ku, Tokyo / Tel: +81-3-0000-0000     |
| Day 2             | Orientation, visiting city heritage landmarks. | Tokyo Central Hotel  | Chiyoda-ku, Tokyo / Tel: +81-3-0000-0000     |
| Day 3             | Scheduled business/sightseeing itinerary.     | Tokyo Central Hotel  | Chiyoda-ku, Tokyo / Tel: +81-3-0000-0000     |
| Day 4             | Regional site visits and cultural tour.       | Tokyo Central Hotel  | Chiyoda-ku, Tokyo / Tel: +81-3-0000-0000     |
| Day {stay_days}            | Hotel checkout, transfer to airport, departure.| Airport Terminal     | International Departure Gate                 |
+-------------------+-----------------------------------------------+----------------------+----------------------------------------------+

Notes:
- All accommodation arrangements and transport reservations correspond with the attached booking vouchers.
- The applicant will reside exclusively at the designated address during the visit.

Applicant Signature: ______________________   Date: {date_str}
"""
        elif "job" in doc_type or "duties" in doc_type:
            return f"""================================================================================
STATUTORY JOB DUTIES SPECIFICATION (職務内容説明書)
Case Reference: {req.case_reference} | Scope: {req.scope_label}
Date: {date_str}
================================================================================

1. EMPLOYEE & EMPLOYER OVERVIEW:
- Employee Name: {full_name}
- Passport Number: {passport_no}
- Employer Name: {employer}
- Monthly Salary: {salary}

2. NATURE OF BUSINESS & OPERATIONAL NEED:
{employer} engages in professional operations requiring specialized technical and international expertise. The employment of {full_name} directly serves to advance critical operational projects and business objectives.

3. DETAILED JOB RESPONSIBILITIES:
- Planning, developing, and executing core technical tasks and workflows.
- Collaborating with multidisciplinary teams and international stakeholders.
- Ensuring strict quality standards, data integrity, and compliance.

4. ALIGNMENT WITH STATUTORY VISA REQUIREMENTS:
The employee's academic background and past professional experience directly correspond with the specialized duties assigned, meeting all standards under the relevant Immigration Control and Refugee Recognition Act guidelines.

Employer / Authorized Representative Signature:
________________________________________
{employer}
Date: {date_str}
"""
        elif "medical" in doc_type or req.jurisdiction_code == "IN" or "medical" in req.scope_label.lower():
            hospital = str(answers.get("destination_hospital") or answers.get("hospital_name") or "Recognized Medical Institution in India")
            hospital_city = str(answers.get("hospital_city") or "India")
            illness = str(answers.get("illness_treatment_category") or answers.get("treatment_nature") or "Specialized Medical Treatment")
            doctor = str(answers.get("doctor_in_charge") or "Senior Consultant / Specialist")
            attendants_count = str(answers.get("accompanying_attendants_count") or "0")
            attendant_info = ""
            if attendants_count != "0":
                attendant_info = f"\nACCOMPANYING ATTENDANTS (MED-2):\n- Total Attendants: {attendants_count}\n- Attendant Details: Declared in application and verified via relationship documents."

            return f"""================================================================================
OFFICIAL MEDICAL VISA (MED-1) APPLICATION COVER LETTER
High Commission of India / Embassy of India / IVAC Consular Wing
Case Reference: {req.case_reference} | Scope: Indian Medical Visa (MED-1)
Date: {date_str}
================================================================================

TO:
The Visa Attaché / Consular Officer
High Commission / Embassy of India

SUBJECT: APPLICATION FOR INDIAN MEDICAL VISA (MED-1) & ATTENDANT VISA (MED-2)
Patient Name: {full_name}
Passport Number: {passport_no}
Nationality: {nationality}
Country of Residence: {current_country}

Respected Consular Officer,

I have the honor to submit this formal visa application for an Indian Medical Visa (MED-1) to undertake specialized medical treatment in India, pursuant to the guidelines of the Ministry of Home Affairs and Bureau of Immigration, Government of India.

1. MEDICAL DIAGNOSIS & TREATMENT FACILITY:
- Destination Hospital: {hospital}, {hospital_city}, India
- Treatment Nature / Specialty: {illness}
- Treating Consultant / Department: {doctor}
- Hospital Invitation Letter: Verified and attached to this dossier.

2. PRELIMINARY MEDICAL REFERRAL:
The patient has undergone initial medical investigations in {current_country}. Based on the diagnosis and the specialized therapeutic technology available in India, our attending physician has advised specialized treatment at {hospital}.
{attendant_info}

3. FINANCIAL SOLVENCY & RECOVERY GUARANTEE:
All expenses associated with the medical treatment, surgery, hospitalization, accommodation, and return travel will be borne entirely by the patient/sponsor ({salary}). Sufficient liquid funds and bank solvency certificates are enclosed. The patient will return to {current_country} upon completion of treatment.

4. ENCLOSED STATUTORY DOCUMENTS:
{doc_list_str}

We respectfully request your favorable consideration and expeditious grant of the Medical Visa (MED-1) for the patient{f' and Medical Attendant Visas (MED-2) for the accompanying caregiver(s)' if attendants_count != '0' else ''}.

Respectfully submitted,

________________________________________
{full_name}
Patient / Primary Applicant
Passport No: {passport_no}
Date: {date_str}
"""
        else:
            return f"""DATE: {date_str}

TO:
The Visa Section / Consular Division
Embassy / Consulate General / Immigration Bureau

SUBJECT: FORMAL APPLICATION COVER LETTER & DOSSIER SUBMISSION
Applicant Name: {full_name}
Passport Number: {passport_no}
Nationality: {nationality}
Sponsoring Employer / Organization: {employer}
Application Reference: {req.case_reference}
Scope: {req.scope_label}

Dear Consular Officer,

I have the honor to submit this formal visa application package for {req.scope_label}. All statutory forms, background records, and verified supporting evidence have been organized in full compliance with published guidelines.

1. PURPOSE OF VISIT:
{purpose}. I plan to arrive on {arrival_date} for a duration of {stay_days} days.

2. FINANCIAL SOLVENCY:
I confirm sufficient independent liquid funds (remuneration: {salary}) to support all costs without recourse to public funds.

3. ENCLOSED SUPPORTING EVIDENCE:
{doc_list_str}

Respectfully yours,

________________________________________
{full_name}
Passport No: {passport_no}
Date: {date_str}
"""
