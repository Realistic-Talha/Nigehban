"""
Seed script for Nigehban database.

Populates the database with realistic demo data for testing and development.

Usage:
    python tooling/scripts/seed.py

Environment:
    DATABASE_URL: PostgreSQL connection string (optional, uses localhost default)
"""

import asyncio
import hashlib
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add apps/api to path so we can import app.models
project_root = Path(__file__).parent.parent.parent.resolve()
api_path = project_root / "apps" / "api"
sys.path.insert(0, str(api_path))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import ProgrammingError

# Import models after path setup
from app.models import ScamPattern, Claim, MediaCheck, TrendSnapshot

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/nigehban"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# =============================================================================
# SCAM PATTERNS (30+ entries - Pakistani context)
# =============================================================================

SCAM_PATTERNS = [
    # Prize/Lottery scams
    {
        "pattern_text": "Congratulations! You won Rs. 50 lakh from Jazz lottery. Send CNIC and mobile number to claim prize within 24 hours.",
        "scam_type": "prize_lottery",
        "description_en": "Fake Jazz lottery prize notification asking for personal information",
        "description_ur": "جعلی جاز لاٹری انعام کی اطلاع جو ذاتی معلومات مانگتی ہے",
    },
    {
        "pattern_text": "Mubarak ho! Aap ne Telenor lucky draw mein Rs. 25 lakh jeet liye hain. Claim karne ke liye 0300-XXXXXXX par rabta karein.",
        "scam_type": "prize_lottery",
        "description_en": "Fake Telenor lucky draw prize in Urdu",
        "description_ur": "اردو میں جعلی ٹیلینر لکی ڈرا انعام",
    },
    {
        "pattern_text": "You have been selected for Rs. 10 lakh prize from PTA. Pay Rs. 5000 processing fee to Easypaisa 03XX-XXXXXXX to receive your prize.",
        "scam_type": "prize_lottery",
        "description_en": "Fake PTA prize requiring advance fee payment",
        "description_ur": "جعلی پی ٹی اے انعام جس کے لیے ایڈوانس فیس درکار ہے",
    },
    
    # Fake bank messages
    {
        "pattern_text": "ALERT: Your HBL account will be blocked in 24 hours. Update your information at https://hbl-verify.com immediately.",
        "scam_type": "bank_phishing",
        "description_en": "Fake HBL account blocking threat with phishing link",
        "description_ur": "جعلی ایچ بی ایل اکاؤنٹ بلاک کرنے کی دھمکی فشنگ لنک کے ساتھ",
    },
    {
        "pattern_text": "Dear Customer, your UBL debit card has been suspended. Verify your identity: http://ubl-security.net",
        "scam_type": "bank_phishing",
        "description_en": "Fake UBL card suspension phishing attempt",
        "description_ur": "جعلی یو بی ایل کارڈ معطلی فشنگ کوشش",
    },
    {
        "pattern_text": "MCB Bank: Suspicious activity detected on your account. Call 042-XXXXXXX immediately or your account will be frozen.",
        "scam_type": "bank_phishing",
        "description_en": "Fake MCB security alert with fraudulent phone number",
        "description_ur": "جعلی ایم سی بی سیکیورٹی الرٹ دھوکہ دہی والے فون نمبر کے ساتھ",
    },
    {
        "pattern_text": "Aap ke Allied Bank account se Rs. 50,000 nikal liye gaye. Agar ye aap ne nahi kiya to 0300-XXXXXXX par call karein.",
        "scam_type": "bank_phishing",
        "description_en": "Fake Allied Bank withdrawal alert in Urdu",
        "description_ur": "اردو میں جعلی الائیڈ بینک رقم نکلوانے کا الرٹ",
    },
    
    # Investment fraud
    {
        "pattern_text": "Earn Rs. 50,000 daily from home! Join our WhatsApp investment group. 100% guaranteed returns. Invest Rs. 10,000 and earn Rs. 50,000 in 7 days.",
        "scam_type": "investment_fraud",
        "description_en": "Unrealistic investment returns via WhatsApp group",
        "description_ur": "واٹس ایپ گروپ کے ذریعے غیر حقیقی سرمایہ کاری منافع",
    },
    {
        "pattern_text": "Ghar baithe Rs. 1 lakh mahana kamayein! Bas Rs. 5000 invest karein aur 30 din mein double returns payein.",
        "scam_type": "investment_fraud",
        "description_en": "Work-from-home investment scheme in Urdu",
        "description_ur": "اردو میں گھر بیٹھے سرمایہ کاری اسکیم",
    },
    {
        "pattern_text": "Join Pakistan's #1 trading platform! Earn Rs. 25,000 daily with just Rs. 5000 investment. Limited seats available!",
        "scam_type": "investment_fraud",
        "description_en": "Fake trading platform with unrealistic daily returns",
        "description_ur": "غیر حقیقی روزانہ منافع کے ساتھ جعلی ٹریڈنگ پلیٹ فارم",
    },
    
    # Job scams
    {
        "pattern_text": "URGENT: Work from home, earn 1 lakh monthly! No experience needed. Send Rs. 2000 registration fee to Easypaisa 03XX-XXXXXXX.",
        "scam_type": "job_scam",
        "description_en": "Fake job offer requiring registration fee",
        "description_ur": "رجسٹریشن فیس درکار جعلی نوکری کی پیشکش",
    },
    {
        "pattern_text": "Daraz is hiring! Work 2 hours daily, earn Rs. 50,000 monthly. Apply now: https://daraz-jobs-pk.com",
        "scam_type": "job_scam",
        "description_en": "Fake Daraz job offer with phishing website",
        "description_ur": "فشنگ ویب سائٹ کے ساتھ جعلی دراز جاب آفر",
    },
    {
        "pattern_text": "YouTube video dekh kar paisa kamayein! Rozana Rs. 5000. Pehle Rs. 1500 registration fee dein.",
        "scam_type": "job_scam",
        "description_en": "Fake YouTube watching job in Urdu",
        "description_ur": "اردو میں یوٹیوب ویڈیو دیکھنے کی جعلی نوکری",
    },
    
    # Government impersonation
    {
        "pattern_text": "NADRA: Your CNIC has been blocked due to verification issues. Visit https://nadra-verification.pk or call 051-XXXXXXX to unblock.",
        "scam_type": "government_impersonation",
        "description_en": "Fake NADRA CNIC blocking message with phishing link",
        "description_ur": "فشنگ لنک کے ساتھ جعلی نادرا شناختی کارڈ بلاک پیغام",
    },
    {
        "pattern_text": "FBR Notice: You owe Rs. 2,50,000 in unpaid taxes. Pay immediately to avoid arrest. Details: https://fbr-tax-notice.com",
        "scam_type": "government_impersonation",
        "description_en": "Fake FBR tax notice threatening arrest",
        "description_ur": "گرفتاری کی دھمکی کے ساتھ جعلی ایف بی آر ٹیکس نوٹس",
    },
    {
        "pattern_text": "BISP: Aap ko Rs. 25,000 ki qist mili hai. Easypaisa account verify karne ke liye 03XX-XXXXXXX par rabta karein.",
        "scam_type": "government_impersonation",
        "description_en": "Fake BISP payment notification in Urdu",
        "description_ur": "اردو میں جعلی بی آئی ایس پی ادائیگی کی اطلاع",
    },
    {
        "pattern_text": "Passport Office: Your passport application is pending. Complete biometric verification at https://passport-gov-pk.com",
        "scam_type": "government_impersonation",
        "description_en": "Fake passport office phishing attempt",
        "description_ur": "جعلی پاسپورٹ آفس فشنگ کوشش",
    },
    
    # Utility bill scams
    {
        "pattern_text": "LESCO: Your electricity will be disconnected tomorrow due to unpaid bill of Rs. 45,000. Pay now: https://lesco-bill-pay.com",
        "scam_type": "utility_scam",
        "description_en": "Fake LESCO disconnection notice with phishing link",
        "description_ur": "فشنگ لنک کے ساتھ جعلی لیسکو بجلی منقطع کرنے کا نوٹس",
    },
    {
        "pattern_text": "SNGPL: Gas bill overdue Rs. 18,500. Connection will be cut in 48 hours. Pay online: https://sngpl-payment.pk",
        "scam_type": "utility_scam",
        "description_en": "Fake SNGPL gas bill payment scam",
        "description_ur": "جعلی ایس این جی پی ایل گیس بل ادائیگی اسکیم",
    },
    {
        "pattern_text": "K-Electric: Aap ka bijli ka bill ada na hone ki wajah se connection kal kat diya jayega. Foran payment karein.",
        "scam_type": "utility_scam",
        "description_en": "Fake K-Electric disconnection threat in Urdu",
        "description_ur": "اردو میں کے الیکٹرک کی جعلی منقطع کرنے کی دھمکی",
    },
    
    # Fake charity
    {
        "pattern_text": "Donation for flood victims: Send zakat/fitrana via Easypaisa 03XX-XXXXXXX. Help our brothers in Sindh. Every rupee counts!",
        "scam_type": "fake_charity",
        "description_en": "Fake flood relief charity asking for Easypaisa donations",
        "description_ur": "ایزی پیسہ ڈونیشن مانگنے والی جعلی سیلاب امداد چیریٹی",
    },
    {
        "pattern_text": "Edhi Foundation appeal: Donate for earthquake victims via JazzCash 0300-XXXXXXX. 100% goes to victims.",
        "scam_type": "fake_charity",
        "description_en": "Fake Edhi Foundation donation scam",
        "description_ur": "جعلی ایدھی فاؤنڈیشن ڈونیشن اسکیم",
    },
    
    # SIM blocking scams
    {
        "pattern_text": "PTA: Your SIM will be blocked in 24 hours due to non-verification. Verify now: https://pta-sim-verify.pk or call 051-XXXXXXX.",
        "scam_type": "sim_block_scam",
        "description_en": "Fake PTA SIM blocking message with phishing link",
        "description_ur": "فشنگ لنک کے ساتھ جعلی پی ٹی اے سم بلاک پیغام",
    },
    {
        "pattern_text": "Jazz: Aap ki SIM 24 ghanton mein block ho jayegi. Verify karne ke liye ye link click karein: http://jazz-verify.com",
        "scam_type": "sim_block_scam",
        "description_en": "Fake Jazz SIM verification scam in Urdu",
        "description_ur": "اردو میں جعلی جاز سم تصدیق اسکیم",
    },
    {
        "pattern_text": "Zong: Your number 03XX-XXXXXXX is not registered. Complete biometric verification or face disconnection.",
        "scam_type": "sim_block_scam",
        "description_en": "Fake Zong registration threat",
        "description_ur": "جعلی زونگ رجسٹریشن دھمکی",
    },
    
    # Cryptocurrency/forex scams
    {
        "pattern_text": "Join our Bitcoin trading group! Earn 50% profit weekly. Start with just Rs. 10,000. WhatsApp: +92-3XX-XXXXXXX",
        "scam_type": "crypto_scam",
        "description_en": "Fake Bitcoin trading group with unrealistic returns",
        "description_ur": "غیر حقیقی منافع کے ساتھ جعلی بٹ کوائن ٹریڈنگ گروپ",
    },
    {
        "pattern_text": "Forex trading se ghar baithe lakho kamayein! Humare experts aap ko sikhayenge. Join karein WhatsApp group.",
        "scam_type": "crypto_scam",
        "description_en": "Fake forex trading scheme in Urdu",
        "description_ur": "اردو میں جعلی فاریکس ٹریڈنگ اسکیم",
    },
    
    # Mobile money scams
    {
        "pattern_text": "Easypaisa: Send Rs. 1000 to 03XX-XXXXXXX to activate your account. This is a mandatory verification step.",
        "scam_type": "mobile_money_scam",
        "description_en": "Fake Easypaisa account activation requiring money transfer",
        "description_ur": "رقم کی منتقلی درکار جعلی ایزی پیسہ اکاؤنٹ ایکٹیویشن",
    },
    {
        "pattern_text": "JazzCash: Aap ka account verify karne ke liye Rs. 500 bhejein 0300-XXXXXXX par. Ye sirf verification ke liye hai.",
        "scam_type": "mobile_money_scam",
        "description_en": "Fake JazzCash verification asking for money in Urdu",
        "description_ur": "اردو میں رقم مانگنے والی جعلی جاز کیش تصدیق",
    },
    {
        "pattern_text": "Congratulations! You received Rs. 50,000 on Easypaisa. To withdraw, send Rs. 2000 processing fee first.",
        "scam_type": "mobile_money_scam",
        "description_en": "Fake Easypaisa prize requiring advance fee",
        "description_ur": "ایڈوانس فیس درکار جعلی ایزی پیسہ انعام",
    },
    
    # WhatsApp forwarding scams
    {
        "pattern_text": "Forward this message to 10 people or your WhatsApp will be deactivated in 24 hours! This is not a joke.",
        "scam_type": "whatsapp_chain",
        "description_en": "WhatsApp chain message threatening account deactivation",
        "description_ur": "اکاؤنٹ غیر فعال کرنے کی دھمکی والا واٹس ایپ چین میسج",
    },
    {
        "pattern_text": "WhatsApp is becoming paid! Forward to 20 contacts to keep it free. If you don't, you'll be charged Rs. 500/month.",
        "scam_type": "whatsapp_chain",
        "description_en": "Fake WhatsApp paid subscription chain message",
        "description_ur": "جعلی واٹس ایپ پیڈ سبسکرپشن چین میسج",
    },
    {
        "pattern_text": "WARNING: If you don't forward this to 15 people, WhatsApp will delete your account. This is the last warning!",
        "scam_type": "whatsapp_chain",
        "description_en": "Aggressive WhatsApp forwarding threat",
        "description_ur": "جارحانہ واٹس ایپ فارورڈنگ دھمکی",
    },
    
    # Marriage/relationship scams
    {
        "pattern_text": "Beautiful girl from Lahore wants to marry you! Contact matchmaker Aunty at 03XX-XXXXXXX. Send Rs. 5000 for meeting arrangement.",
        "scam_type": "marriage_scam",
        "description_en": "Fake marriage proposal requiring payment for arrangement",
        "description_ur": "ملاقات کے انتظام کے لیے ادائیگی درکار جعلی شادی کی پیشکش",
    },
    {
        "pattern_text": "Overseas Pakistani looking for bride. Family will send Rs. 5 lakh as gift. First send Rs. 10,000 for visa processing.",
        "scam_type": "marriage_scam",
        "description_en": "Fake overseas Pakistani marriage proposal scam",
        "description_ur": "جعلی بیرون ملک پاکستانی شادی کی پیشکش اسکیم",
    },
    
    # Phishing links disguised as Pakistani brands
    {
        "pattern_text": "Daraz Mega Sale! Up to 90% off on all items. Shop now: https://daraz-sale-2024.com (Today only!)",
        "scam_type": "brand_phishing",
        "description_en": "Fake Daraz sale phishing website",
        "description_ur": "جعلی دراز سیل فشنگ ویب سائٹ",
    },
    {
        "pattern_text": "Foodpanda: Aap ka order confirm karne ke liye payment details update karein: https://foodpanda-pk-verify.com",
        "scam_type": "brand_phishing",
        "description_en": "Fake Foodpanda payment verification in Urdu",
        "description_ur": "اردو میں جعلی فوڈ پانڈا ادائیگی تصدیق",
    },
    {
        "pattern_text": "Careem ride cancelled. Refund of Rs. 2500 pending. Click to receive: https://careem-refund.pk",
        "scam_type": "brand_phishing",
        "description_en": "Fake Careem refund phishing link",
        "description_ur": "جعلی کریم رقم واپسی فشنگ لنک",
    },
]


# =============================================================================
# FACT-CHECK CLAIMS (20+ entries - Pakistan-relevant)
# =============================================================================

FACT_CHECK_CLAIMS = [
    # Political claims
    {
        "title": "ECP announces election results within 2 hours of polling closing",
        "body": "Multiple social media posts claim that the Election Commission of Pakistan announced final results within 2 hours, suggesting pre-poll rigging.",
        "category": "politics",
        "verdict": "false",
        "confidence_score": 0.92,
        "explanation_en": "The ECP does not announce final results within 2 hours. Preliminary results are released gradually over several hours/days as counting completes. This claim misrepresents the official election process.",
        "explanation_ur": "الیکشن کمیشن آف پاکستان 2 گھنٹے میں حتمی نتائج کا اعلان نہیں کرتا۔ ابتدائی نتائج گنتی مکمل ہونے پر کئی گھنٹوں/دنوں میں آہستہ آہستہ جاری کیے جاتے ہیں۔ یہ دعویٰ سرکاری انتخابی عمل کو غلط انداز میں پیش کرتا ہے۔",
        "sources": [
            {"url": "https://ecp.gov.pk", "title": "Election Commission of Pakistan Official Website"},
            {"url": "https://www.dawn.com/news/elections-2024", "title": "Dawn News Election Coverage"}
        ],
        "language": "en",
    },
    {
        "title": "Government to impose 50% tax on all salary holders",
        "body": "WhatsApp forwards claim the government is planning to tax 50% of all salaried employees' income starting next month.",
        "category": "politics",
        "verdict": "false",
        "confidence_score": 0.95,
        "explanation_en": "No such tax policy exists. Pakistan's income tax rates vary by income bracket, with the highest rate around 35% for top earners. This is misinformation designed to create panic.",
        "explanation_ur": "ایسی کوئی ٹیکس پالیسی موجود نہیں ہے۔ پاکستان کے انکم ٹیکس کی شرحیں آمدنی کے لحاظ سے مختلف ہیں، سب سے زیادہ شرح تقریباً 35% ہے۔ یہ خوف پھیلانے کے لیے غلط معلومات ہیں۔",
        "sources": [
            {"url": "https://www.fbr.gov.pk", "title": "Federal Board of Revenue"},
            {"url": "https://www.reuters.com/world/asia-pacific/pakistan-tax-policy", "title": "Reuters Pakistan Tax Coverage"}
        ],
        "language": "en",
    },
    {
        "title": "Imran Khan released from Adiala Jail",
        "body": "Social media posts claim Imran Khan has been released from Adiala Jail and is addressing supporters.",
        "category": "politics",
        "verdict": "unverified",
        "confidence_score": 0.65,
        "explanation_en": "This claim is circulating without official confirmation. PTI leadership has not issued any statement. Court proceedings are ongoing. Verify with official sources before sharing.",
        "explanation_ur": "یہ دعویٰ سرکاری تصدیق کے بغیر گردش کر رہا ہے۔ پی ٹی آئی قیادت نے کوئی بیان جاری نہیں کیا۔ عدالتی کارروائی جاری ہے۔ شیئر کرنے سے پہلے سرکاری ذرائع سے تصدیق کریں۔",
        "sources": [
            {"url": "https://www.geo.tv/latest-news", "title": "Geo News Latest Updates"}
        ],
        "language": "en",
    },
    
    # Health misinformation
    {
        "title": "Polio vaccine causes infertility in Pakistani children",
        "body": "Viral video claims polio drops contain chemicals that make children infertile, urging parents to refuse vaccination.",
        "category": "health",
        "verdict": "false",
        "confidence_score": 0.98,
        "explanation_en": "Polio vaccines are safe and WHO-certified. Pakistan is one of the last polio-endemic countries, and vaccination is crucial. This misinformation has contributed to vaccine hesitancy and polio outbreaks.",
        "explanation_ur": "پولیو ویکسین محفوظ اور ڈبلیو ایچ او سے منظور شدہ ہے۔ پاکستان پولیو سے متاثرہ آخری ممالک میں سے ایک ہے، اور ویکسینیشن بہت ضروری ہے۔ یہ غلط معلومات ویکسین سے گریز اور پولیو پھیلنے کا سبب بنی ہیں۔",
        "sources": [
            {"url": "https://www.who.int/news-room/fact-sheets/detail/poliomyelitis", "title": "WHO Polio Fact Sheet"},
            {"url": "https://www.endpolio.org.pk", "title": "Pakistan Polio Eradication Programme"}
        ],
        "language": "en",
    },
    {
        "title": "Drinking warm water with lemon cures cancer",
        "body": "Forwarded message claims a doctor from Pakistan Army revealed that warm lemon water kills cancer cells.",
        "category": "health",
        "verdict": "false",
        "confidence_score": 0.94,
        "explanation_en": "No scientific evidence supports this claim. While healthy diet is important, cancer requires proper medical treatment. Such misinformation can delay critical treatment and harm patients.",
        "explanation_ur": "اس دعوے کی حمایت میں کوئی سائنسی ثبوت نہیں ہے۔ صحت مند غذا اہم ہے، لیکن کینسر کو مناسب طبی علاج کی ضرورت ہے۔ ایسی غلط معلومات اہم علاج میں تاخیر کر سکتی ہیں۔",
        "sources": [
            {"url": "https://www.cancer.org", "title": "American Cancer Society"},
            {"url": "https://www.shaukatkhanum.org.pk", "title": "Shaukat Khanum Cancer Hospital"}
        ],
        "language": "en",
    },
    {
        "title": "COVID-19 vaccines contain microchips for tracking",
        "body": "Claims that COVID vaccines contain 5G microchips to track Pakistani citizens.",
        "category": "health",
        "verdict": "false",
        "confidence_score": 0.97,
        "explanation_en": "COVID-19 vaccines do not contain microchips or tracking devices. This conspiracy theory has been debunked globally. Vaccines underwent rigorous testing and approval processes.",
        "explanation_ur": "کوویڈ 19 ویکسین میں مائیکرو چپس یا ٹریکنگ آلات نہیں ہیں۔ یہ سازشی نظریہ عالمی سطح پر غلط ثابت ہو چکا ہے۔ ویکسین کی سخت جانچ اور منظوری کا عمل ہوا۔",
        "sources": [
            {"url": "https://www.who.int/emergencies/diseases-novel-coronavirus-2019", "title": "WHO COVID-19 Information"},
            {"url": "https://www.nih.org.pk", "title": "National Institute of Health Pakistan"}
        ],
        "language": "en",
    },
    {
        "title": "Traditional herbal remedy cures diabetes permanently",
        "body": "Advertisement for 'Diabe-Cure' herbal medicine claims to permanently cure diabetes in 30 days without insulin.",
        "category": "health",
        "verdict": "false",
        "confidence_score": 0.93,
        "explanation_en": "Diabetes is a chronic condition that cannot be 'cured' - it requires ongoing management. No herbal remedy has been scientifically proven to cure diabetes. Consult your doctor for proper treatment.",
        "explanation_ur": "ذیابیطس ایک دائمی بیماری ہے جس کا 'علاج' ممکن نہیں - اسے مسلسل کنٹرول کرنے کی ضرورت ہے۔ کسی جڑی بوٹی نے ذیابیطس کا علاج ثابت نہیں کیا۔ مناسب علاج کے لیے اپنے ڈاکٹر سے مشورہ کریں۔",
        "sources": [
            {"url": "https://www.diabetes.org", "title": "American Diabetes Association"}
        ],
        "language": "en",
    },
    
    # Financial claims
    {
        "title": "Pakistani Rupee to be replaced by new currency 'New Pak'",
        "body": "Social media claims that State Bank is introducing 'New Pak' currency, replacing the current Rupee at 1:1 ratio.",
        "category": "finance",
        "verdict": "false",
        "confidence_score": 0.96,
        "explanation_en": "The State Bank of Pakistan has made no such announcement. Currency redenomination is a major policy decision that would be officially communicated through Parliament and media.",
        "explanation_ur": "اسٹیٹ بینک آف پاکستان نے ایسا کوئی اعلان نہیں کیا۔ کرنسی کی تبدیلی ایک بڑا پالیسی فیصلہ ہے جس کا اعلان پارلیمنٹ اور میڈیا کے ذریعے سرکاری طور پر کیا جائے گا۔",
        "sources": [
            {"url": "https://www.sbp.org.pk", "title": "State Bank of Pakistan"}
        ],
        "language": "en",
    },
    {
        "title": "Pakistan's foreign reserves reach $50 billion",
        "body": "Posts claim Pakistan's foreign reserves have hit $50 billion, the highest in history.",
        "category": "finance",
        "verdict": "false",
        "confidence_score": 0.89,
        "explanation_en": "Pakistan's foreign reserves are significantly lower than $50 billion. Current reserves are around $8-10 billion. This claim exaggerates the economic situation.",
        "explanation_ur": "پاکستان کے زر مبادلہ کے ذخائر 50 ارب ڈالر سے بہت کم ہیں۔ موجودہ ذخائر تقریباً 8-10 ارب ڈالر ہیں۔ یہ دعویٰ معاشی صورتحال کو بڑھا چڑھا کر پیش کرتا ہے۔",
        "sources": [
            {"url": "https://www.sbp.org.pk/ecodata/forex.htm", "title": "SBP Foreign Reserves Data"}
        ],
        "language": "en",
    },
    {
        "title": "Government announces Rs. 25,000 monthly stipend for all citizens",
        "body": "Viral message claims every Pakistani citizen will receive Rs. 25,000 monthly from government starting next month.",
        "category": "finance",
        "verdict": "false",
        "confidence_score": 0.91,
        "explanation_en": "No universal basic income program of this scale exists. BISP provides targeted support to specific eligible families, not universal payments. This is misleading information.",
        "explanation_ur": "اس پیمانے کا کوئی عالمی بنیادی آمدنی پروگرام موجود نہیں ہے۔ بی آئی ایس پی مخصوص اہل خاندانوں کو ہدف بنایا گیا سپورٹ فراہم کرتا ہے، عالمی ادائیگیاں نہیں۔ یہ گمراہ کن معلومات ہیں۔",
        "sources": [
            {"url": "https://bisp.gov.pk", "title": "Benazir Income Support Programme"}
        ],
        "language": "en",
    },
    
    # Religious misinformation
    {
        "title": "New mosque construction banned in Islamabad",
        "body": "Claims that the government has banned construction of new mosques in Islamabad's residential areas.",
        "category": "religion",
        "verdict": "false",
        "confidence_score": 0.88,
        "explanation_en": "No such ban exists. While there are zoning regulations for all buildings, there is no specific ban on mosque construction. This is inflammatory misinformation.",
        "explanation_ur": "ایسا کوئی پابندی موجود نہیں ہے۔ اگرچہ تمام عمارتوں کے لیے زوننگ ریگولیشنز ہیں، مسجدوں کی تعمیر پر کوئی خاص پابندی نہیں ہے۔ یہ اشتعال انگیز غلط معلومات ہیں۔",
        "sources": [
            {"url": "https://www.cda.gov.pk", "title": "Capital Development Authority"}
        ],
        "language": "en",
    },
    {
        "title": "Quran recitation banned on loudspeakers after 10 PM",
        "body": "Social media claims police will arrest anyone reciting Quran on loudspeaker after 10 PM.",
        "category": "religion",
        "verdict": "misleading",
        "confidence_score": 0.78,
        "explanation_en": "There are noise regulations limiting loudspeaker use at night in residential areas, but these apply to all loudspeaker use, not specifically Quran recitation. The framing is misleading.",
        "explanation_ur": "رہائشی علاقوں میں رات کو لاؤڈ اسپیکر کے استعمال پر شور کے ضوابط ہیں، لیکن یہ تمام لاؤڈ اسپیکر استعمال پر لاگو ہیں، خاص طور پر قرآن کی تلاوت پر نہیں۔ یہ فریمنگ گمراہ کن ہے۔",
        "sources": [
            {"url": "https://punjablaws.gov.pk", "title": "Punjab Laws Portal"}
        ],
        "language": "en",
    },
    
    # Technology claims
    {
        "title": "5G towers cause cancer and COVID-19",
        "body": "Viral post claims 5G towers in Karachi are causing cancer and spreading COVID-19.",
        "category": "technology",
        "verdict": "false",
        "confidence_score": 0.96,
        "explanation_en": "5G technology does not cause cancer or spread viruses. Pakistan is still in early stages of 5G deployment. This conspiracy has been debunked by WHO and telecom regulators worldwide.",
        "explanation_ur": "5G ٹیکنالوجی کینسر کا سبب نہیں بنتی اور نہ ہی وائرس پھیلاتی ہے۔ پاکستان ابھی 5G کی تعیناتی کے ابتدائی مراحل میں ہے۔ اس سازش کو عالمی سطح پر غلط ثابت کیا گیا ہے۔",
        "sources": [
            {"url": "https://www.who.int/news-room/q-a-detail/5g-mobile-networks-and-health", "title": "WHO 5G and Health"},
            {"url": "https://www.pta.gov.pk", "title": "Pakistan Telecommunication Authority"}
        ],
        "language": "en",
    },
    {
        "title": "WhatsApp to be banned in Pakistan from next month",
        "body": "News circulating that PTA will ban WhatsApp completely starting next month.",
        "category": "technology",
        "verdict": "unverified",
        "confidence_score": 0.55,
        "explanation_en": "PTA periodically discusses encryption and compliance with messaging apps, but no official ban announcement has been made. Previous threats to ban WhatsApp have not materialized.",
        "explanation_ur": "پی ٹی اے وقتاً فوقتاً میسجنگ ایپس کے بارے میں بات کرتا ہے، لیکن کوئی سرکاری پابندی کا اعلان نہیں کیا گیا۔ واٹس ایپ کو پابند کرنے کی پچھلی دھمکیاں عمل میں نہیں آئیں۔",
        "sources": [
            {"url": "https://www.pta.gov.pk", "title": "Pakistan Telecommunication Authority"}
        ],
        "language": "en",
    },
    {
        "title": "TikTok permanently banned in Pakistan",
        "body": "Claims that TikTok has been permanently banned and will never return to Pakistan.",
        "category": "technology",
        "verdict": "false",
        "confidence_score": 0.87,
        "explanation_en": "While TikTok has faced temporary bans in Pakistan, it is currently operational. Social media platforms often face regulatory challenges but 'permanent' bans are rare and usually reversed.",
        "explanation_ur": "اگرچہ ٹک ٹاک کو پاکستان میں عارضی پابندیوں کا سامنا کرنا پڑا ہے، یہ فی الحال کام کر رہا ہے۔ سوشل میڈیا پلیٹ فارمز کو اکثر ریگولیٹری چیلنجز کا سامنا ہوتا ہے لیکن 'مستقل' پابندیاں نایاب ہیں۔",
        "sources": [
            {"url": "https://www.pta.gov.pk", "title": "PTA Official Website"}
        ],
        "language": "en",
    },
    
    # Natural disaster misinformation
    {
        "title": "Karachi will sink into the sea by 2030",
        "body": "Viral report claims Karachi will be completely underwater by 2030 due to climate change.",
        "category": "disaster",
        "verdict": "misleading",
        "confidence_score": 0.75,
        "explanation_en": "While Karachi faces serious flooding risks from sea level rise, the claim of complete submersion by 2030 is grossly exaggerated. Coastal areas are vulnerable, but the timeline and extent are misrepresented.",
        "explanation_ur": "اگرچہ کراچی کو سمندر کی سطح بڑھنے سے سنگین سیلاب کے خطرات ہیں، 2030 تک مکمل ڈوبنے کا دعویٰ بہت بڑھا چڑھا کر پیش کیا گیا ہے۔ ساحلی علاقے خطرے میں ہیں، لیکن ٹائم لائن غلط ہے۔",
        "sources": [
            {"url": "https://www.ndma.gov.pk", "title": "National Disaster Management Authority"}
        ],
        "language": "en",
    },
    {
        "title": "Earthquake of magnitude 9.0 predicted to hit Islamabad",
        "body": "Forwarded message claims scientists predict a massive 9.0 earthquake will destroy Islamabad within weeks.",
        "category": "disaster",
        "verdict": "false",
        "confidence_score": 0.94,
        "explanation_en": "Earthquakes cannot be predicted with specific timing or magnitude. While Pakistan is seismically active, no such prediction exists. This is fear-mongering pseudoscience.",
        "explanation_ur": "زلزلوں کی مخصوص وقت یا شدت کے ساتھ پیشگوئی نہیں کی جا سکتی۔ اگرچہ پاکستان زلزلی سرگرمی والے علاقے میں ہے، ایسی کوئی پیشگوئی موجود نہیں ہے۔ یہ خوف پھیلانے والی سودوسائنس ہے۔",
        "sources": [
            {"url": "https://www.usgs.gov/programs/earthquake-hazards", "title": "USGS Earthquake Hazards Program"}
        ],
        "language": "en",
    },
    
    # Cricket/sports claims
    {
        "title": "Pakistan Cricket Board to ban all foreign players from PSL",
        "body": "Reports claim PCB has decided to ban all foreign players from Pakistan Super League starting next season.",
        "category": "sports",
        "verdict": "false",
        "confidence_score": 0.91,
        "explanation_en": "PCB has made no such announcement. PSL continues to attract international players. Foreign player participation is a key feature of the league.",
        "explanation_ur": "پی سی بی نے ایسا کوئی اعلان نہیں کیا۔ پی ایس ایل بین الاقوامی کھلاڑیوں کو راغب کرنا جاری رکھے ہوئے ہے۔ غیر ملکی کھلاڑیوں کی شرکت لیگ کی اہم خصوصیت ہے۔",
        "sources": [
            {"url": "https://www.pcb.com.pk", "title": "Pakistan Cricket Board"},
            {"url": "https://psl-t20.com", "title": "Pakistan Super League"}
        ],
        "language": "en",
    },
    {
        "title": "Babar Azam retires from international cricket",
        "body": "Breaking news claims Babar Azam has announced immediate retirement from all forms of cricket.",
        "category": "sports",
        "verdict": "false",
        "confidence_score": 0.88,
        "explanation_en": "No such retirement announcement has been made by Babar Azam or PCB. This is fake news designed to generate clicks. Always verify with official sources.",
        "explanation_ur": "بابر اعظم یا پی سی بی کی جانب سے ریٹائرمنٹ کا کوئی اعلان نہیں کیا گیا۔ یہ کلکس حاصل کرنے کے لیے ڈیزائن کی گئی جعلی خبر ہے۔ ہمیشہ سرکاری ذرائع سے تصدیق کریں۔",
        "sources": [
            {"url": "https://www.pcb.com.pk", "title": "Pakistan Cricket Board"}
        ],
        "language": "en",
    },
    {
        "title": "Pakistan wins ICC World Cup 2025",
        "body": "Forwarded message celebrates Pakistan winning the ICC World Cup before the tournament has concluded.",
        "category": "sports",
        "verdict": "false",
        "confidence_score": 0.99,
        "explanation_en": "The tournament has not concluded yet. This is premature celebration or wishful thinking being presented as fact. Tournament results should be verified from official ICC sources.",
        "explanation_ur": "ٹورنامنٹ ابھی ختم نہیں ہوا ہے۔ یہ حقیقت کے طور پر پیش کی جانے والی قبل از وقت جشن یا خواہش ہے۔ ٹورنامنٹ کے نتائج کی تصدیق سرکاری آئی سی سی ذرائع سے کرنی چاہیے۔",
        "sources": [
            {"url": "https://www.icc-cricket.com", "title": "International Cricket Council"}
        ],
        "language": "en",
    },
    
    # Satire example
    {
        "title": "Pakistani scientist invents flying rickshaw",
        "body": "Satirical article claims a Pakistani scientist has invented a flying rickshaw that will solve traffic problems.",
        "category": "satire",
        "verdict": "satire",
        "confidence_score": 0.95,
        "explanation_en": "This is a satirical piece, not real news. It was published on a humor website. While creative solutions are welcome, flying rickshaws are not currently feasible.",
        "explanation_ur": "یہ ایک طنزیہ مضمون ہے، حقیقی خبر نہیں۔ یہ ایک مزاحیہ ویب سائٹ پر شائع ہوا تھا۔ اگرچہ تخلیقی حل خوش آئند ہیں، اڑنے والے رکشے فی الحال ممکن نہیں ہیں۔",
        "sources": [
            {"url": "https://khabaristan.com", "title": "Khabaristan (Satire Site)"}
        ],
        "language": "en",
    },
    
    # Additional claim
    {
        "title": "All private schools to be nationalized",
        "body": "Parents receiving messages claiming government will take over all private schools and convert them to government schools.",
        "category": "politics",
        "verdict": "false",
        "confidence_score": 0.93,
        "explanation_en": "No such nationalization policy exists or has been proposed. Private schools operate under provincial education authorities' regulations. This is misinformation causing unnecessary panic among parents.",
        "explanation_ur": "ایسی کوئی قومیا پالیسی موجود نہیں ہے اور نہ ہی تجویز کی گئی ہے۔ نجی اسکول صوبائی تعلیمی حکام کے ضوابط کے تحت کام کرتے ہیں۔ یہ والدین میں غیر ضروری خوف پھیلانے والی غلط معلومات ہیں۔",
        "sources": [
            {"url": "https://punjab.gov.pk/education", "title": "Punjab Education Department"}
        ],
        "language": "en",
    },
]


# =============================================================================
# MEDIA CHECK ENTRIES (5 entries)
# =============================================================================

MEDIA_CHECKS = [
    {
        "media_type": "image",
        "file_url": "https://example.com/media/claim_001_protest.jpg",
        "authenticity_score": 0.85,
        "signals": {
            "metadata_consistency": "valid",
            "noise_analysis": "normal",
            "compression_artifacts": "consistent",
            "source_verification": "partially_verified",
        },
        "verdict": "likely_authentic",
        "explanation_en": "Image appears authentic based on metadata and noise analysis. Minor inconsistencies in EXIF data suggest possible re-saving but no manipulation detected.",
        "explanation_ur": "میٹا ڈیٹا اور نوائز تجزیہ کی بنیاد پر تصویر اصلی لگتی ہے۔ EXIF ڈیٹا میں معمولی تضادات دوبارہ محفوظ کرنے کی تجویز دیتے ہیں لیکن کوئی ہیرا پھیری نہیں ملی۔",
    },
    {
        "media_type": "image",
        "file_url": "https://example.com/media/politician_speech.jpg",
        "authenticity_score": 0.32,
        "signals": {
            "metadata_consistency": "suspicious",
            "noise_analysis": "inconsistent_regions",
            "compression_artifacts": "mismatched",
            "source_verification": "not_found",
            "face_detection": "altered",
        },
        "verdict": "likely_manipulated",
        "explanation_en": "Image shows strong signs of manipulation. Noise patterns are inconsistent across regions, suggesting compositing. Face appears to have been altered or replaced.",
        "explanation_ur": "تصویر ہیرا پھیری کی مضبوط علامات دکھاتی ہے۔ نوائز پیٹرن علاقوں میں متضاد ہیں، جو کمپوزیٹنگ کی تجویز دیتے ہیں۔ چہرہ تبدیل یا بدلنے کا لگتا ہے۔",
    },
    {
        "media_type": "video",
        "file_url": "https://example.com/media/flood_footage.mp4",
        "authenticity_score": 0.45,
        "signals": {
            "metadata_consistency": "missing",
            "temporal_analysis": "splices_detected",
            "frame_consistency": "variable",
            "source_verification": "unverifiable",
        },
        "verdict": "inconclusive",
        "explanation_en": "Video authenticity cannot be conclusively determined. Some temporal inconsistencies detected but may be due to editing rather than manipulation. Original source needed for verification.",
        "explanation_ur": "ویڈیو کی صداقت حتمی طور پر نہیں کی جا سکتی۔ کچھ عارضی تضادات ملے ہیں لیکن یہ ایڈیٹنگ کی وجہ سے ہو سکتے ہیں۔ تصدیق کے لیے اصل ذریعہ درکار ہے۔",
    },
    {
        "media_type": "image",
        "file_url": "https://example.com/media/cricket_victory.jpg",
        "authenticity_score": 0.92,
        "signals": {
            "metadata_consistency": "valid",
            "noise_analysis": "uniform",
            "compression_artifacts": "consistent",
            "source_verification": "verified_reuters",
            "reverse_search": "no_prior_matches",
        },
        "verdict": "likely_authentic",
        "explanation_en": "Image verified as authentic. Metadata is consistent, noise patterns are uniform, and reverse image search confirms it was first published by Reuters news agency.",
        "explanation_ur": "تصویر اصلی کے طور پر تصدیق شدہ۔ میٹا ڈیٹا مستقل ہے، نوائز پیٹرن یکساں ہیں، اور ریورس امیج سرچ نے تصدیق کی کہ پہلے رائٹرز نیوز ایجنسی نے شائع کی۔",
    },
    {
        "media_type": "image",
        "file_url": "https://example.com/media/deepfake_politician.png",
        "authenticity_score": 0.18,
        "signals": {
            "metadata_consistency": "fabricated",
            "noise_analysis": "ai_generated_patterns",
            "compression_artifacts": "gan_artifacts",
            "source_verification": "no_source",
            "face_detection": "deepfake_detected",
            "gaze_direction": "abnormal",
        },
        "verdict": "likely_manipulated",
        "explanation_en": "This image is almost certainly AI-generated (deepfake). GAN artifacts detected, gaze direction is abnormal, and no legitimate source exists. This is synthetic media.",
        "explanation_ur": "یہ تصویر یقینی طور پر AI سے تیار کردہ (ڈیپ فیک) ہے۔ GAN آثار ملے، نظروں کی سمت غیر معمولی ہے، اور کوئی جائز ذریعہ موجود نہیں۔ یہ مصنوعی میڈیا ہے۔",
    },
]


# =============================================================================
# TREND SNAPSHOTS (10 entries)
# =============================================================================

def build_trend_snapshots(claims: list[Claim], scam_patterns: list[ScamPattern]):
    """Build trend snapshots linked to existing claims and scam patterns."""
    snapshots = []
    
    # Link some claims
    for i, claim in enumerate(claims[:6]):
        snapshots.append({
            "related_entity_id": claim.id,
            "entity_type": "claim",
            "report_volume": (i + 1) * 150 + 50,
            "spread_score": round(0.3 + (i * 0.08), 2),
        })
    
    # Link some scam patterns
    for i, pattern in enumerate(scam_patterns[:4]):
        snapshots.append({
            "related_entity_id": pattern.id,
            "entity_type": "scam_report",
            "report_volume": (i + 1) * 200 + 100,
            "spread_score": round(0.5 + (i * 0.1), 2),
        })
    
    return snapshots


# =============================================================================
# MAIN SEEDING LOGIC
# =============================================================================

async def check_tables_exist(session: AsyncSession) -> bool:
    """Check if required tables exist in the database."""
    try:
        await session.execute(text("SELECT 1 FROM scam_patterns LIMIT 1"))
        await session.execute(text("SELECT 1 FROM claims LIMIT 1"))
        await session.execute(text("SELECT 1 FROM media_checks LIMIT 1"))
        await session.execute(text("SELECT 1 FROM trend_snapshots LIMIT 1"))
        return True
    except ProgrammingError:
        return False


async def seed_scam_patterns(session: AsyncSession) -> list[ScamPattern]:
    """Insert scam patterns, skipping duplicates."""
    inserted = []
    skipped = 0
    
    for data in SCAM_PATTERNS:
        content_hash = compute_hash(data["pattern_text"])
        
        # Check for existing
        result = await session.execute(
            select(ScamPattern).where(
                ScamPattern.pattern_text == data["pattern_text"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            inserted.append(existing)
            skipped += 1
            continue
        
        pattern = ScamPattern(
            id=uuid4(),
            pattern_text=data["pattern_text"],
            scam_type=data["scam_type"],
            description_en=data["description_en"],
            description_ur=data["description_ur"],
            times_reported=0,
        )
        session.add(pattern)
        inserted.append(pattern)
    
    await session.flush()
    print(f"  ✓ Scam patterns: {len(inserted) - skipped} new, {skipped} existing")
    return inserted


async def seed_claims(session: AsyncSession) -> list[Claim]:
    """Insert fact-check claims, skipping duplicates."""
    inserted = []
    skipped = 0
    
    for data in FACT_CHECK_CLAIMS:
        content_hash = compute_hash(data["title"] + (data.get("body") or ""))
        
        # Check for existing
        result = await session.execute(
            select(Claim).where(Claim.title == data["title"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            inserted.append(existing)
            skipped += 1
            continue
        
        claim = Claim(
            id=uuid4(),
            title=data["title"],
            body=data.get("body"),
            category=data.get("category"),
            verdict=data.get("verdict"),
            confidence_score=data.get("confidence_score"),
            explanation_en=data.get("explanation_en"),
            explanation_ur=data.get("explanation_ur"),
            sources=data.get("sources"),
            language=data.get("language", "en"),
            content_hash=content_hash,
        )
        session.add(claim)
        inserted.append(claim)
    
    await session.flush()
    print(f"  ✓ Claims: {len(inserted) - skipped} new, {skipped} existing")
    return inserted


async def seed_media_checks(session: AsyncSession) -> list[MediaCheck]:
    """Insert media check entries, skipping duplicates."""
    inserted = []
    skipped = 0
    
    for data in MEDIA_CHECKS:
        file_hash = compute_hash(data["file_url"])
        
        # Check for existing
        result = await session.execute(
            select(MediaCheck).where(MediaCheck.file_hash == file_hash)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            inserted.append(existing)
            skipped += 1
            continue
        
        media_check = MediaCheck(
            id=uuid4(),
            media_type=data["media_type"],
            file_url=data["file_url"],
            file_hash=file_hash,
            authenticity_score=data["authenticity_score"],
            signals=data["signals"],
            verdict=data["verdict"],
            explanation_en=data["explanation_en"],
            explanation_ur=data["explanation_ur"],
        )
        session.add(media_check)
        inserted.append(media_check)
    
    await session.flush()
    print(f"  ✓ Media checks: {len(inserted) - skipped} new, {skipped} existing")
    return inserted


async def seed_trend_snapshots(
    session: AsyncSession, claims: list[Claim], scam_patterns: list[ScamPattern]
) -> list[TrendSnapshot]:
    """Insert trend snapshots linked to claims and scam patterns."""
    inserted = []
    
    snapshot_data = build_trend_snapshots(claims, scam_patterns)
    
    for data in snapshot_data:
        # Check for existing snapshot for this entity
        result = await session.execute(
            select(TrendSnapshot).where(
                TrendSnapshot.related_entity_id == data["related_entity_id"],
                TrendSnapshot.entity_type == data["entity_type"],
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing snapshot
            existing.report_volume = data["report_volume"]
            existing.spread_score = data["spread_score"]
            inserted.append(existing)
            continue
        
        snapshot = TrendSnapshot(
            id=uuid4(),
            related_entity_id=data["related_entity_id"],
            entity_type=data["entity_type"],
            report_volume=data["report_volume"],
            spread_score=data["spread_score"],
        )
        session.add(snapshot)
        inserted.append(snapshot)
    
    await session.flush()
    print(f"  ✓ Trend snapshots: {len(inserted)} entries")
    return inserted


async def main():
    """Main seeding function."""
    print("=" * 60)
    print("Nigehban Database Seeder")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL.split('@')[-1]}")
    print()
    
    async with AsyncSessionLocal() as session:
        # Check if tables exist
        print("Checking database tables...")
        tables_exist = await check_tables_exist(session)
        
        if not tables_exist:
            print("\n✗ ERROR: Required tables not found in database.")
            print("  Please run migrations first:")
            print("    cd apps/api && alembic upgrade head")
            print()
            return
        
        print("✓ Tables found\n")
        
        # Seed scam patterns
        print("Seeding scam patterns...")
        scam_patterns = await seed_scam_patterns(session)
        
        # Seed claims
        print("Seeding fact-check claims...")
        claims = await seed_claims(session)
        
        # Seed media checks
        print("Seeding media check entries...")
        media_checks = await seed_media_checks(session)
        
        # Seed trend snapshots
        print("Seeding trend snapshots...")
        trend_snapshots = await seed_trend_snapshots(session, claims, scam_patterns)
        
        # Commit all changes
        await session.commit()
        
        # Summary
        print("\n" + "=" * 60)
        print("Seeding Complete!")
        print("=" * 60)
        print(f"  Scam Patterns:    {len(scam_patterns)}")
        print(f"  Claims:           {len(claims)}")
        print(f"  Media Checks:     {len(media_checks)}")
        print(f"  Trend Snapshots:  {len(trend_snapshots)}")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSeeding interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)
