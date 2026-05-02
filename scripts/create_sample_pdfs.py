"""
Creates sample government policy PDFs using fpdf2 for pipeline testing.
Run: python create_sample_pdfs.py
"""
from fpdf import FPDF
from pathlib import Path

RAW_PDF_DIR = Path(__file__).parent / "data_pipeline" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_DOCUMENTS = [
    {
        "filename": "UGC_Scholarship_Policy_2024.pdf",
        "title": "UGC Scholarship Policy 2024",
        "content": [
            ("Section 1: Eligibility Criteria",
             "Students must have secured a minimum of 60% aggregate marks in their previous qualifying examination. "
             "The scholarship is available to students enrolled in recognized universities under the UGC Act. "
             "Students from economically weaker sections (EWS) with annual family income below Rs. 8 lakh per annum are eligible. "
             "Reservation as per government norms: SC/ST (22.5%), OBC (27%), PwD (5%)."),
            ("Section 2: Scholarship Amount",
             "The maximum scholarship amount for undergraduate students is Rs. 12,000 per annum. "
             "For postgraduate students, the scholarship amount is Rs. 20,000 per annum. "
             "PhD scholars receive a fellowship of Rs. 31,000 per month for the first two years "
             "and Rs. 35,000 per month for the remaining tenure. "
             "An additional contingency allowance of Rs. 10,000 per annum is provided for research expenses."),
            ("Section 3: Application Process",
             "Applications must be submitted through the National Scholarship Portal (https://scholarships.gov.in). "
             "Required documents: Aadhaar card, income certificate, previous mark sheets, bank passbook, "
             "caste certificate (if applicable), and domicile certificate. "
             "The application window opens every year from 1st July to 30th September. "
             "Incomplete applications will be rejected without any notification."),
            ("Section 4: Renewal Conditions",
             "Scholarships are renewed annually subject to satisfactory academic performance. "
             "Students must maintain a minimum attendance of 75% in all subjects. "
             "A minimum of 60% marks in annual/semester examinations is mandatory for renewal. "
             "Change in course or institution requires prior approval from the UGC scholarship cell."),
        ]
    },
    {
        "filename": "NEP_2020_Implementation_Guidelines.pdf",
        "title": "National Education Policy 2020 - Implementation Guidelines",
        "content": [
            ("Chapter 1: Overview of NEP 2020",
             "The National Education Policy 2020 (NEP 2020) replaces the National Policy on Education 1986. "
             "It aims to transform India into a global knowledge superpower by 2040. "
             "The policy envisions an education system rooted in Indian ethos that contributes directly "
             "to transforming India sustainably into an equitable and vibrant knowledge society."),
            ("Chapter 2: School Education Reforms",
             "The 10+2 structure is replaced with 5+3+3+4 curricular structure covering ages 3 to 18. "
             "Foundational stage (ages 3-8): 3 years of preschool + Classes 1 and 2. "
             "Preparatory stage (ages 8-11): Classes 3, 4, and 5. "
             "Middle stage (ages 11-14): Classes 6, 7, and 8. "
             "Secondary stage (ages 14-18): Classes 9, 10, 11, and 12. "
             "Mother tongue or regional language to be medium of instruction until Grade 5."),
            ("Chapter 3: Higher Education Reforms",
             "The three-language formula will be implemented across all schools. "
             "Sanskrit and other classical languages will be offered at all levels. "
             "An undergraduate degree will be of 3 or 4 years duration with multiple exit points. "
             "The Academic Bank of Credits (ABC) will be established for storing and transferring credits. "
             "The National Research Foundation (NRF) will be set up to foster research culture. "
             "Target: 50% Gross Enrollment Ratio in higher education by 2035."),
            ("Chapter 4: Teacher Education",
             "By 2030, the minimum degree qualification for teaching will be a 4-year integrated B.Ed. degree. "
             "National Professional Standards for Teachers (NPST) will be developed by NCTE. "
             "Regular performance appraisal of teachers will be conducted based on predefined criteria. "
             "Teachers will receive continuous professional development through online and offline training."),
        ]
    },
    {
        "filename": "Gazette_Notification_Faculty_Promotions.pdf",
        "title": "Gazette Notification: Faculty Promotion Rules - Ministry of Education",
        "content": [
            ("Notification No. MoE/HR/2024/001",
             "In exercise of the powers conferred by Section 26(1)(g) of the University Grants Commission Act, 1956, "
             "the following regulations regarding Career Advancement Scheme (CAS) for faculty promotions are hereby notified. "
             "These regulations come into force from the date of their publication in the Official Gazette."),
            ("Clause 3: Eligibility for Promotion - Assistant Professor to Associate Professor",
             "An Assistant Professor shall be eligible for promotion to Associate Professor after completing "
             "8 years of service as Assistant Professor (Stages 1, 2, and 3 combined cannot exceed 8 years). "
             "Minimum Academic Performance Indicator (API) score of 300 points is mandatory. "
             "At least one Ph.D. thesis supervision as supervisor or co-supervisor is required. "
             "A minimum of 2 peer-reviewed publications in UGC Care-listed journals during the assessment period."),
            ("Clause 4: Eligibility for Promotion - Associate Professor to Professor",
             "An Associate Professor shall be eligible for promotion to Professor after completing "
             "3 years of service as Associate Professor. "
             "Minimum API score of 400 points is mandatory for the assessment period. "
             "At least 3 research publications in UGC Care-listed or Scopus-indexed journals. "
             "Evidence of Ph.D. theses supervised (minimum 2 candidates awarded) is required."),
            ("Clause 5: API Scoring System",
             "Category I: Teaching, Learning and Evaluation - Maximum 125 points per year. "
             "Category II: Co-curricular, Research and Administration - Maximum 100 points per year. "
             "Category III: Research and Academic Contributions - Publications carry variable scores from 25 to 75 points. "
             "API scores are self-reported and subject to verification by the Selection Committee."),
        ]
    },
]


def create_pdf(doc: dict) -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, doc["title"], ln=True, align="C")
    pdf.ln(6)

    for section_title, section_body in doc["content"]:
        # Add new page if near bottom
        if pdf.get_y() > 230:
            pdf.add_page()

        # Section heading
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, section_title, ln=True)
        pdf.ln(2)

        # Section body (split long text across lines)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, section_body)
        pdf.ln(6)

    dest = RAW_PDF_DIR / doc["filename"]
    pdf.output(str(dest))
    size_kb = dest.stat().st_size // 1024
    print(f"  ✅ Created: {doc['filename']} ({size_kb} KB, {len(doc['content'])} sections)")
    return dest


if __name__ == "__main__":
    # Remove the fake (HTML) files we downloaded earlier
    for fake in ["UGC_Act.pdf", "UGC_NEP_Policy.pdf"]:
        f = RAW_PDF_DIR / fake
        if f.exists():
            f.unlink()
            print(f"  🗑️  Removed fake file: {fake}")

    print("\n=== Creating Sample Policy PDFs ===\n")
    for doc in SAMPLE_DOCUMENTS:
        create_pdf(doc)

    pdfs = list(RAW_PDF_DIR.glob("*.pdf"))
    print(f"\n✅ {len(pdfs)} PDF(s) ready. Run: python data_pipeline/embed_and_store.py")
