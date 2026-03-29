import streamlit as st
from google import genai  # 最新のgoogle-genaiライブラリを使用
import datetime
import json
import os
import requests
import textwrap
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# 1. ページ基本設定
st.set_page_config(page_title="美肌処方箋ジェネレーター | Luxia", layout="centered")

# 2. セキュリティ：裏側のSecretsから取得（ブラックボックス仕様）
try:
    api_key = st.secrets["GEMINI_API_KEY"].strip()
except Exception:
    st.error("ライセンス認証エラー：管理者（株式会社Luxia）へお問い合わせください。")
    st.stop()

# --- 日本語フォントの自動取得と設定 ---
@st.cache_resource
def setup_japanese_font():
    font_path = "MPLUS1p-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://raw.githubusercontent.com/google/fonts/main/ofl/mplus1p/MPLUS1p-Regular.ttf"
        response = requests.get(url)
        if response.status_code == 200:
            with open(font_path, "wb") as f:
                f.write(response.content)
    pdfmetrics.registerFont(TTFont("MPLUS1p", font_path))
    return "MPLUS1p"

# --- UIのスタイリング ---
st.markdown("""
    <style>
    .prescription-box { border: 2px solid #555; padding: 25px; border-radius: 10px; background-color: #f9f9f9; margin-top: 20px; }
    .rx-title { color: #2c3e50; text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 5px; }
    .rx-header { font-size: 16px; color: #555; text-align: right; }
    .salon-treatment { font-weight: bold; color: #2c3e50; font-size: 1.2em; border-bottom: 2px solid #e67e22; padding-bottom: 2px; }
    .usage-step { font-weight: bold; color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

def draw_wrapped_text(c, text, x, y, max_chars, line_height):
    lines = textwrap.wrap(text, width=max_chars)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y

# --- PDF生成関数 ---
def create_pdf(customer_name, staff_name, date_str, rx_data, font_name, salon_name):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    c.setFont(font_name, 10)
    c.drawRightString(width - 15*mm, height - 15*mm, f"診断日: {date_str}")
    c.drawRightString(width - 15*mm, height - 20*mm, f"担当スタッフ: {staff_name}")
    c.drawRightString(width - 15*mm, height - 25*mm, f"発行元: {salon_name}")
    
    c.setFont(font_name, 24)
    c.drawCentredString(width/2, height - 40*mm, "美肌処方箋 (Rx)")
    
    c.setFont(font_name, 16)
    c.drawString(20*mm, height - 55*mm, f"{customer_name} 専用ケアプラン")
    
    text_y = height - 70*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "【プロフェッショナル・アドバイス】")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    advice = rx_data.get("advice", "")
    text_y = draw_wrapped_text(c, advice, 25*mm, text_y, max_chars=40, line_height=6*mm)
    
    text_y -= 5*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "🌙 朝のケア (Morning)")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    for i, product in enumerate(rx_data.get("morning_routine_products", [])):
        text_y = draw_wrapped_text(c, f"STEP{i+1}: {product}", 25*mm, text_y, max_chars=40, line_height=6*mm)
        
    text_y -= 5*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "☀️ 夜のケア (Evening)")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    for i, product in enumerate(rx_data.get("evening_routine_products", [])):
        text_y = draw_wrapped_text(c, f"STEP{i+1}: {product}", 25*mm, text_y, max_chars=40, line_height=6*mm)

    text_y -= 5*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "💡 サロン推奨施術のご提案")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    treatment = rx_data.get("recommended_salon_treatment", "")
    text_y = draw_wrapped_text(c, f"・ {treatment}", 25*mm, text_y, max_chars=40, line_height=6*mm)
    
    c.setFont(font_name, 10)
    c.drawCentredString(width/2, 20*mm, f"Copyright (C) {datetime.date.today().year} {salon_name} All Rights Reserved.")
    c.save()
    buffer.seek(0)
    return buffer

# --- メイン画面 ---
st.title("🛡️ AI 自動生成「美肌処方箋」")
st.markdown("10項目の詳細解析から、お客様専用のPDF処方箋を生成します。")

with st.sidebar:
    st.header("⚙️ 導入サロン設定")
    salon_name = st.text_input("サロン名", value="株式会社Luxia 美容研究所")
    custom_treatments = st.text_area(
        "推奨施術メニュー",
        value="・高濃度ビタミンC導入 (シミ、くすみ)\n・ハーブピーリング (毛穴、肌荒れ)\n・幹細胞フェイシャル (ハリ、小じわ)\n・ラジオ波フェイシャル (たるみ、むくみ)"
    )
    st.divider()
    customer_name = st.text_input("お客様名", value="山田 花子 様")
    staff_name = st.text_input("担当スタッフ", value="佐藤 美記")
    skin_type = st.selectbox("肌質", ["乾燥肌", "脂性肌", "混合肌", "普通肌", "敏感肌"])
    main_concerns = st.multiselect("主なお悩み", ["乾燥・カサつき", "ニキビ・肌荒れ", "シミ・くすみ", "ハリ不足・小じわ", "毛穴の目立ち", "テカリ・べたつき"])
    st.divider()
    # ライフスタイル質問（短縮表示）
    ans_sleep = st.selectbox("Q1. 睡眠", ["特に問題なし", "6時間未満", "不規則", "眠りが浅い"])
    ans_diet = st.selectbox("Q2. 食生活", ["特に問題なし", "甘いもの好き", "脂っこいもの好き", "外食が多い"])
    ans_env = st.selectbox("Q3. 環境", ["特に問題なし", "エアコン内", "屋外多い", "PC長時間"])
    ans_excercise = st.selectbox("Q4. 運動", ["週数回", "しない", "シャワーのみ", "湯船派"])
    ans_skincare = st.selectbox("Q5. ケア習慣", ["丁寧", "オイル派", "ダブル洗顔", "時短派"])
    ans_stress = st.selectbox("Q6. ストレス", ["なし", "あり", "顔に出る", "常に疲労"])
    ans_water = st.selectbox("Q7. 水分", ["1.5L以上", "茶・珈琲", "飲まない"])
    ans_uv = st.selectbox("Q8. UV対策", ["年中", "夏のみ", "しない"])
    ans_cycle = st.selectbox("Q9. ゆらぎ", ["安定", "生理前", "季節変り", "常に不安定"])
    ans_goal = st.selectbox("Q10. 理想", ["透明感", "ハリツヤ", "なめらか", "毛穴レス"])

    st.divider()
    generate_btn = st.button("AI 美肌処方箋を生成する", type="primary", use_container_width=True)

if generate_btn:
    if not main_concerns:
        st.error("お悩みを1つ以上選択してください。")
    else:
        with st.status("AIが処方箋を構成中...", expanded=True) as status:
            try:
                font_name = setup_japanese_font()
                client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
                
                prompt = f"""
                あなたは日本のサロン専属トップエステティシャンです。顧客データを分析しJSON形式で回答してください。
                顧客：{customer_name}（{skin_type}）
                悩み：{', '.join(main_concerns)}
                理想：{ans_goal}
                生活習慣：睡眠[{ans_sleep}]、食事[{ans_diet}]、環境[{ans_env}]、ストレス[{ans_stress}]、UV[{ans_uv}]
                
                製品情報:
                - ROMAN スキンケアローション (基礎保湿)
                - NIVORA クリアバランシングセラム (肌荒れ・毛穴用)
                - NIVORA リッチモイスチャークリーム (乾燥・エイジング用)
                
                導入サロンの施術メニュー:
                {custom_treatments}
                
                ### 出力形式 (JSON)
                {{
                  "advice": "120文字程度のアドバイス",
                  "morning_routine_products": ["製品名 (使い方)"],
                  "evening_routine_products": ["製品名 (使い方)"],
                  "recommended_salon_treatment": "最適な施術名1つとその理由"
                }}
                """
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                
                # JSON抽出
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                rx_data = json.loads(clean_json)
                
                pdf_file = create_pdf(customer_name, staff_name, str(datetime.date.today()), rx_data, font_name, salon_name)
                
                st.divider()
                st.success("✅ 処方箋の生成が完了しました！")
                st.download_button("📥 PDF処方箋をダウンロード", data=pdf_file, file_name=f"美肌処方箋_{customer_name}.pdf", mime="application/pdf", use_container_width=True)

                # 画面表示
                st.markdown("<div class='prescription-box'>", unsafe_allow_html=True)
                st.markdown("<p class='rx-title'>美肌処方箋 (Rx)</p>", unsafe_allow_html=True)
                st.subheader(f"✨ {customer_name} 専用ケアプラン")
                st.info(rx_data.get("advice", ""))
                st.markdown(f"💡 推奨施術: <span class='salon-treatment'>{rx_data.get('recommended_salon_treatment', '')}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                status.update(label="処方箋の発行が完了しました！", state="complete")

            except Exception as e:
                status.update(label="エラー発生", state="error")
                st.error(f"生成エラー: {e}")

st.divider()
st.caption("© 2026 株式会社Luxia | サロン物販をAIで支援する")
