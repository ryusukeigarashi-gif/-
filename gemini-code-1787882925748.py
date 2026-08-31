import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import plotly.express as px

# ---------------------------------------------------------
# 1. データベース初期化＆マスタ保持
# ---------------------------------------------------------
DB_FILE = "work_management.db"

def is_other_task(task_name):
    return "その他" in str(task_name)

def is_apa_shousai(task_name):
    return "アパ詳細" in str(task_name)

def init_sqlite_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT,
            user_name TEXT,
            category TEXT,
            task_name TEXT,
            work_hours REAL,
            processed_count INTEGER,
            target_uph REAL,
            notes TEXT
        )
    ''')
    
    try:
        c.execute("ALTER TABLE daily_logs ADD COLUMN other_hours REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS category_user_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            UNIQUE(category, name)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS task_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            task_name TEXT,
            UNIQUE(category, task_name)
        )
    ''')

    c.execute("SELECT COUNT(*) FROM category_user_master")
    if c.fetchone()[0] == 0:
        default_category_users = [
            ("商品情報", "栗原"), ("商品情報", "橋口"), ("商品情報", "飯塚"), ("商品情報", "杉守"),
            ("撮影", "古賀"), ("撮影", "笠鳥"), ("撮影", "萩中"), ("撮影", "街"), 
            ("撮影", "小松"), ("撮影", "岡"), ("撮影", "細川"), ("撮影", "澤田"), ("撮影", "小林"),
            ("工程管理", "加藤"), ("工程管理", "澤田"), ("工程管理", "小林"), ("工程管理", "末廣")
        ]
        for cat, u in default_category_users:
            c.execute("INSERT OR IGNORE INTO category_user_master (category, name) VALUES (?, ?)", (cat, u))

    c.execute("SELECT COUNT(*) FROM task_master")
    if c.fetchone()[0] == 0:
        default_tasks = [
            ("商品情報", "ダメージ・詳細・採寸（PD）"),
            ("商品情報", "アパ詳細"),
            ("商品情報", "衣類検品"),
            ("商品情報", "ヤフオク出品"),
            ("商品情報", "その他業務"),
            ("商品情報", "その他業務(チーム内)"),
            ("商品情報", "その他業務(チーム外)"),
            ("撮影", "撮影のみ（通常）"),
            ("撮影", "OUTLET撮影"),
            ("撮影", "ヤフオク撮影"),
            ("撮影", "その他業務"),
            ("撮影", "その他業務(チーム内)"),
            ("撮影", "その他業務(チーム外)"),
            ("工程管理", "基幹（取込・移動・入庫）"),
            ("工程管理", "新規出品入庫"),
            ("工程管理", "その他入庫（LIVE/EU/ETC）"),
            ("工程管理", "仕分け・返送梱包"),
            ("工程管理", "その他業務"),
            ("工程管理", "その他業務(チーム内)"),
            ("工程管理", "その他業務(チーム外)")
        ]
        for cat, task in default_tasks:
            c.execute("INSERT OR IGNORE INTO task_master (category, task_name) VALUES (?, ?)", (cat, task))

    conn.commit()
    conn.close()

init_sqlite_db()

def get_users_by_category():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT category, name FROM category_user_master ORDER BY id")
    rows = c.fetchall()
    conn.close()
    
    user_dict = {"商品情報": [], "撮影": [], "工程管理": []}
    for cat, name in rows:
        if cat in user_dict:
            user_dict[cat].append(name)
    return user_dict

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT name FROM category_user_master ORDER BY id")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users if users else ["（未登録）"]

def get_task_master():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT category, task_name FROM task_master ORDER BY id")
    rows = c.fetchall()
    conn.close()
    
    task_dict = {"商品情報": [], "撮影": [], "工程管理": []}
    for cat, task in rows:
        if cat in task_dict:
            task_dict[cat].append(task)
    return task_dict

# ---------------------------------------------------------
# 2. マスターデータ・基本設定
# ---------------------------------------------------------
st.set_page_config(page_title="作業処理数・可処分管理アプリ", layout="wide")

st.markdown("""
<style>
div[data-testid="column"] {
    padding: 0px 2px;
}
button {
    width: 100%;
    margin-bottom: 5px;
}
</style>
""", unsafe_allow_html=True)

st.title("📦 可処分・作業処理数管理システム")

CATEGORY_USER_MASTER = get_users_by_category()
ALL_USERS = get_all_users()
TASK_MASTER = get_task_master()

def insert_log(work_date, user_name, category, task_name, work_hours, processed_count, notes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO daily_logs (work_date, user_name, category, task_name, work_hours, processed_count, target_uph, notes)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    ''', (pd.to_datetime(work_date).strftime("%Y-%m-%d"), user_name, category, task_name, float(work_hours), int(processed_count), str(notes)))
    conn.commit()
    conn.close()

def update_log(log_id, work_date, user_name, category, task_name, work_hours, processed_count, notes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE daily_logs 
        SET work_date = ?, user_name = ?, category = ?, task_name = ?, work_hours = ?, processed_count = ?, notes = ?
        WHERE id = ?
    ''', (work_date.strftime("%Y-%m-%d"), user_name, category, task_name, work_hours, processed_count, notes, log_id))
    conn.commit()
    conn.close()

def delete_log(log_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM daily_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

COLUMN_JAPANESE_MAP = {
    'id': 'ID',
    'work_date': '作業日',
    'user_name': '担当者名',
    'category': '業務カテゴリ',
    'task_name': '詳細作業',
    'work_hours': '稼働時間(h)',
    'processed_count': '処理数',
    'task_uph': '作業UPH(明細)',
    'actual_uph': '実質UPH',
    'notes': '備考・共有事項'
}

def compute_summary_uph(df_agg):
    df_agg['作業UPH'] = df_agg.apply(
        lambda r: round(r['valid_processed_count'] / (r['work_hours'] - r['other_hours']), 2) 
        if (r['work_hours'] - r['other_hours']) > 0 else 0, axis=1)
    
    df_agg['実質UPH'] = df_agg.apply(
        lambda r: round(r['valid_processed_count'] / r['work_hours'], 2) 
        if r['work_hours'] > 0 else 0, axis=1)
    
    return df_agg

# ---------------------------------------------------------
# コールバック関数群 (セッション状態を安全に更新)
# ---------------------------------------------------------
def set_hours_cb(key, val):
    st.session_state[key] = float(val)

def add_hours_cb(key, delta):
    st.session_state[key] = max(0.0, round(float(st.session_state[key]) + delta, 2))

def reset_hours_cb(key):
    st.session_state[key] = 0.0

def add_count_cb(key, delta):
    st.session_state[key] = max(0, int(st.session_state[key]) + delta)

def reset_count_cb(key):
    st.session_state[key] = 0

def submit_form_cb(cat_key, category_name):
    date_val = st.session_state[f"d_{cat_key}"]
    user_val = st.session_state[f"user_sel_{cat_key}"]
    task_val = st.session_state[f"task_sel_{cat_key}"]
    hours_val = st.session_state[f"hours_val_{cat_key}"]
    count_val = st.session_state[f"count_val_{cat_key}"]
    notes_val = st.session_state.get(f"n_{cat_key}", "")

    insert_log(date_val, user_val, category_name, task_val, hours_val, count_val, notes_val)

    uph = round(count_val / hours_val, 2) if hours_val > 0 and not is_other_task(task_val) else 0

    st.session_state[f"count_val_{cat_key}"] = 0
    st.session_state[f"hours_val_{cat_key}"] = 0.0

    msg_key = f"msg_{cat_key}"
    if is_other_task(task_val):
        st.session_state[msg_key] = f"🎉 {date_val} {user_val}さんの「{category_name}（{task_val}）」を登録しました。（その他業務として計上）"
    else:
        st.session_state[msg_key] = f"🎉 {date_val} {user_val}さんの「{category_name}（{task_val}）」を登録しました！（作業UPH: {uph}）"

# ---------------------------------------------------------
# 3. 画面構成
# ---------------------------------------------------------
main_tab1, main_tab2, main_tab3, main_tab4, main_tab5, main_tab6 = st.tabs([
    "📝 作業実績入力", "✏️ 登録実績の修正・削除", "📊 業務別ダッシュボード", "📈 個人・UPH分析", "⚙️ マスタ管理", "📥 CSV一括取り込み"
])

# ==========================================
# TAB 1: 作業実績入力
# ==========================================
with main_tab1:
    st.subheader("日次作業実績の入力")
    
    input_tab1, input_tab2, input_tab3 = st.tabs(["💻 商品情報", "📸 撮影", "📦 工程管理"])

    def render_intuitive_input_form(cat_key, category_name):
        users = CATEGORY_USER_MASTER.get(category_name, [])
        tasks = TASK_MASTER.get(category_name, [])

        msg_key = f"msg_{cat_key}"
        user_key = f"user_sel_{cat_key}"
        task_key = f"task_sel_{cat_key}"
        hours_key = f"hours_val_{cat_key}"
        count_key = f"count_val_{cat_key}"

        if msg_key in st.session_state and st.session_state[msg_key]:
            st.success(st.session_state[msg_key])
            st.session_state[msg_key] = ""

        if not users or not tasks:
            st.warning(f"「{category_name}」の担当者または詳細作業が未登録です。「⚙️ マスタ管理」から追加してください。")
            return

        if user_key not in st.session_state or st.session_state[user_key] not in users:
            st.session_state[user_key] = users[0]
        if task_key not in st.session_state or st.session_state[task_key] not in tasks:
            st.session_state[task_key] = tasks[0]
        if hours_key not in st.session_state:
            st.session_state[hours_key] = 0.0
        if count_key not in st.session_state:
            st.session_state[count_key] = 0

        st.markdown("##### 👤 **1. 日付と担当者を選択**")
        col_d, col_u = st.columns([1, 3])
        with col_d:
            st.date_input("作業日", date.today(), key=f"d_{cat_key}")
        with col_u:
            st.radio("担当者名", users, key=user_key, horizontal=True, label_visibility="collapsed")

        st.markdown("---")
        st.markdown("##### 📋 **2. 詳細作業を選択**")
        st.radio("詳細作業名", tasks, key=task_key, horizontal=True, label_visibility="collapsed")

        st.markdown("---")
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("##### ⏱️ **3. 稼働時間 (時間)**")
            
            h_inc1 = [0.25, 0.5, 1.0, 2.0, 3.0]
            btn_cols_h1 = st.columns(len(h_inc1))
            for idx, inc in enumerate(h_inc1):
                with btn_cols_h1[idx]:
                    st.button(f"+{inc}h", key=f"btn_h1_{cat_key}_{inc}", on_click=add_hours_cb, args=(hours_key, inc))

            h_inc2 = [4.0, 5.0, 6.0, 7.0, 8.0]
            btn_cols_h2 = st.columns(len(h_inc2))
            for idx, inc in enumerate(h_inc2):
                with btn_cols_h2[idx]:
                    st.button(f"+{inc}h", key=f"btn_h2_{cat_key}_{inc}", on_click=add_hours_cb, args=(hours_key, inc))

            btn_cols_h3 = st.columns(3)
            with btn_cols_h3[0]:
                st.button("➖ 0.25h", key=f"btn_h_sub_{cat_key}", on_click=add_hours_cb, args=(hours_key, -0.25))
            with btn_cols_h3[1]:
                st.button("➕ 0.25h", key=f"btn_h_add_{cat_key}", on_click=add_hours_cb, args=(hours_key, 0.25))
            with btn_cols_h3[2]:
                st.button("🔄 リセット", key=f"btn_h_reset_{cat_key}", on_click=reset_hours_cb, args=(hours_key,))

            st.number_input(
                "（手入力も可能）",
                min_value=0.0,
                max_value=24.0,
                step=0.25,
                key=hours_key
            )

        with col_right:
            st.markdown("##### 🔢 **4. 処理数 (点/箱)**")
            
            increments = [1, 5, 10, 50, 100]
            btn_cols_c = st.columns(len(increments))
            for idx, inc in enumerate(increments):
                with btn_cols_c[idx]:
                    st.button(f"+{inc}", key=f"btn_c_add_{cat_key}_{inc}", on_click=add_count_cb, args=(count_key, inc))
            
            btn_cols_c2 = st.columns([4, 1])
            with btn_cols_c2[1]:
                st.button("🔄", key=f"btn_c_reset_{cat_key}", on_click=reset_count_cb, args=(count_key,))

            st.number_input(
                "（手入力も可能）",
                min_value=0,
                step=1,
                key=count_key
            )

        st.text_input("備考・共有事項（任意）", key=f"n_{cat_key}")

        st.markdown("---")
        st.button(
            f"✅ 【{category_name}】の実績を登録する",
            type="primary",
            use_container_width=True,
            key=f"btn_submit_{cat_key}",
            on_click=submit_form_cb,
            args=(cat_key, category_name)
        )

    with input_tab1:
        render_intuitive_input_form("s", "商品情報")

    with input_tab2:
        render_intuitive_input_form("p", "撮影")

    with input_tab3:
        render_intuitive_input_form("k", "工程管理")

    st.markdown("---")
    st.subheader("🔍 個人・日別入力確認（業務別内訳）")
    
    col_chk1, col_chk2 = st.columns(2)
    with col_chk1:
        chk_date = st.date_input("確認したい日付", date.today(), key="chk_d")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_name FROM daily_logs WHERE work_date = ? ORDER BY user_name", (chk_date.strftime("%Y-%m-%d"),))
    date_active_users = [row[0] for row in c.fetchall()]
    conn.close()

    with col_chk2:
        if date_active_users:
            chk_user = st.selectbox("確認したい担当者名", ["全員"] + date_active_users, key="chk_u")
        else:
            chk_user = st.selectbox("確認したい担当者名", ["（選択日に登録者なし）"], key="chk_u")

    conn = sqlite3.connect(DB_FILE)
    query = "SELECT id, work_date, user_name, category, task_name, work_hours, processed_count, notes FROM daily_logs WHERE work_date = ?"
    params = [chk_date.strftime("%Y-%m-%d")]
    
    if chk_user != "全員" and chk_user != "（選択日に登録者なし）":
        query += " AND user_name = ?"
        params.append(chk_user)
        
    query += " ORDER BY id DESC"
    df_day_user = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df_day_user.empty and chk_user != "（選択日に登録者なし）":
        df_day_user['is_other'] = df_day_user['task_name'].astype(str).str.contains("その他")
        df_day_user['is_apa'] = df_day_user['task_name'].astype(str).str.contains("アパ詳細")
        
        df_day_user['other_hours'] = df_day_user.apply(lambda r: r['work_hours'] if r['is_other'] else 0, axis=1)
        df_day_user['valid_processed_count'] = df_day_user.apply(lambda r: 0 if r['is_apa'] else r['processed_count'], axis=1)
        
        df_day_user['task_uph'] = df_day_user.apply(lambda r: 0 if r['is_other'] else round(r['processed_count'] / r['work_hours'], 2) if r['work_hours'] > 0 else 0, axis=1)
        df_day_user['actual_uph'] = df_day_user.apply(lambda r: round(r['processed_count'] / r['work_hours'], 2) if r['work_hours'] > 0 else 0, axis=1)

        cols_order = ['id', 'work_date', 'user_name', 'category', 'task_name', 'work_hours', 'processed_count', 'task_uph', 'actual_uph', 'notes']

        chk_tab_all, chk_tab_s, chk_tab_p, chk_tab_k = st.tabs([
            "🌐 全体明細", "💻 商品情報", "📸 撮影", "📦 工程管理"
        ])

        with chk_tab_all:
            tot_hours = df_day_user['work_hours'].sum()
            tot_other = df_day_user['other_hours'].sum()
            tot_valid_count = df_day_user['valid_processed_count'].sum() 
            
            avg_task_uph = round(tot_valid_count / (tot_hours - tot_other), 2) if (tot_hours - tot_other) > 0 else 0
            avg_act_uph = round(tot_valid_count / tot_hours, 2) if tot_hours > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("【全体】総稼働時間", f"{tot_hours:.2f} 時間")
            m2.metric("【全体】総処理数（アパ除く）", f"{tot_valid_count:,} 点")
            m3.metric("【全体】作業UPH", f"{avg_task_uph:.2f}")
            m4.metric("【全体】実質UPH", f"{avg_act_uph:.2f}")

            st.markdown("##### 📝 明細データ一覧")
            df_day_user_jp = df_day_user[cols_order].rename(columns=COLUMN_JAPANESE_MAP)
            st.dataframe(df_day_user_jp, use_container_width=True)

        for tab_obj, cat_title in [(chk_tab_s, "商品情報"), (chk_tab_p, "撮影"), (chk_tab_k, "工程管理")]:
            with tab_obj:
                df_sub = df_day_user[df_day_user['category'] == cat_title]
                if not df_sub.empty:
                    sub_h = df_sub['work_hours'].sum()
                    sub_o = df_sub['other_hours'].sum()
                    sub_c = df_sub['valid_processed_count'].sum() 
                    
                    sub_task_uph = round(sub_c / (sub_h - sub_o), 2) if (sub_h - sub_o) > 0 else 0
                    sub_act_uph = round(sub_c / sub_h, 2) if sub_h > 0 else 0

                    sm1, sm2, sm3, sm4 = st.columns(4)
                    sm1.metric(f"【{cat_title}】総稼働時間", f"{sub_h:.2f} 時間")
                    sm2.metric(f"【{cat_title}】総処理数（アパ除く）", f"{sub_c:,} 点")
                    sm3.metric(f"【{cat_title}】作業UPH", f"{sub_task_uph:.2f}")
                    sm4.metric(f"【{cat_title}】実質UPH", f"{sub_act_uph:.2f}")

                    st.markdown("##### 📝 明細データ一覧")
                    df_sub_jp = df_sub[cols_order].rename(columns=COLUMN_JAPANESE_MAP)
                    st.dataframe(df_sub_jp, use_container_width=True)
                else:
                    st.info(f"選択された日付・対象者で「{cat_title}」の登録データはありません。")
    else:
        st.info(f"{chk_date.strftime('%Y-%m-%d')} に登録されているデータはありません。")

# ==========================================
# TAB 2: ✏️ 登録実績の修正・削除
# ==========================================
with main_tab2:
    st.subheader("登録済み実績データの修正・削除")
    
    st.markdown("##### 📅 1. 日付を選択してください")
    edit_filter_date = st.date_input("作業日", date.today(), key="edit_filter_d", label_visibility="collapsed")
    target_date_str = edit_filter_date.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_FILE)
    df_date_edit = pd.read_sql_query("SELECT * FROM daily_logs WHERE work_date = ? ORDER BY id DESC", conn, params=[target_date_str])
    conn.close()

    st.markdown("---")

    if df_date_edit.empty:
        st.info(f"{target_date_str} の実績データは登録されていません。")
    else:
        st.markdown("##### 🔍 2. 修正・削除したいデータを選択してください")
        
        df_date_edit['label'] = df_date_edit.apply(
            lambda r: f"【{r['category']}】 {r['user_name']} ｜ {r['task_name']} ({r['work_hours']}h / {r['processed_count']}点)", axis=1
        )
        
        selected_label = st.radio(
            "登録データ一覧", 
            df_date_edit['label'].tolist(), 
            key="edit_select_radio",
            label_visibility="collapsed"
        )
        
        target_row = df_date_edit[df_date_edit['label'] == selected_label].iloc[0]
        target_id = int(target_row['id'])
        current_date = datetime.strptime(target_row['work_date'], "%Y-%m-%d").date()
        current_cat = target_row['category'] if target_row['category'] in ["商品情報", "撮影", "工程管理"] else "商品情報"
        
        st.markdown("---")

        st.markdown(f"##### ✏️ 3. 選択中のデータ（ID: {target_id}）を編集")
        
        with st.container(border=True):
            col_e1, col_e2, col_e3 = st.columns(3)
            
            with col_e1:
                edit_date = st.date_input("作業日", current_date, key="edit_form_date")
                edit_cat = st.selectbox("業務カテゴリ", ["商品情報", "撮影", "工程管理"], index=["商品情報", "撮影", "工程管理"].index(current_cat), key="edit_form_cat")
            
            with col_e2:
                avail_users = CATEGORY_USER_MASTER.get(edit_cat, ALL_USERS)
                avail_tasks = TASK_MASTER.get(edit_cat, ["通常作業"])
                
                user_idx = avail_users.index(target_row['user_name']) if target_row['user_name'] in avail_users else 0
                task_idx = avail_tasks.index(target_row['task_name']) if target_row['task_name'] in avail_tasks else 0
                
                edit_user = st.selectbox("担当者名", avail_users, index=user_idx, key="edit_form_user")
                edit_task = st.selectbox("詳細作業", avail_tasks, index=task_idx, key="edit_form_task")
                
            with col_e3:
                edit_hours = st.number_input("稼働時間 (時間)", min_value=0.0, max_value=24.0, value=float(target_row['work_hours']), step=0.25, key="edit_form_hours")
                edit_count = st.number_input("処理数 (点/箱)", min_value=0, value=int(target_row['processed_count']), step=1, key="edit_form_count")
            
            edit_notes = st.text_input("備考・共有事項", value=str(target_row['notes'] or ''), key="edit_form_notes")

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("💾 この内容で実績を上書き修正する", type="primary", use_container_width=True):
                    update_log(target_id, edit_date, edit_user, edit_cat, edit_task, edit_hours, edit_count, edit_notes)
                    st.success(f"ID:{target_id} の実績データを更新しました。")
                    st.rerun()
            with col_btn2:
                if st.button("🗑️ このデータを完全に削除する", use_container_width=True):
                    delete_log(target_id)
                    st.success(f"ID:{target_id} の実績データを削除しました。")
                    st.rerun()

# ==========================================
# TAB 3: 📊 業務別ダッシュボード
# ==========================================
with main_tab3:
    st.subheader("業務別ダッシュボード・集計")
    
    conn = sqlite3.connect(DB_FILE)
    df_dash = pd.read_sql_query("SELECT * FROM daily_logs", conn)
    conn.close()

    if df_dash.empty:
        st.info("データが登録されていません。")
    else:
        df_dash['is_other'] = df_dash['task_name'].astype(str).str.contains("その他")
        df_dash['is_apa'] = df_dash['task_name'].astype(str).str.contains("アパ詳細")
        
        df_dash['other_hours'] = df_dash.apply(lambda r: r['work_hours'] if r['is_other'] else 0, axis=1)
        df_dash['valid_processed_count'] = df_dash.apply(lambda r: 0 if r['is_apa'] else r['processed_count'], axis=1)

        min_d = pd.to_datetime(df_dash['work_date']).min().date()
        max_d = pd.to_datetime(df_dash['work_date']).max().date()
        selected_dates = st.date_input("集計対象期間", [min_d, date.today()], key="dash_dates")
        
        start_d = selected_dates[0]
        end_d = selected_dates[1] if len(selected_dates) > 1 else selected_dates[0]
        
        df_dash_filtered = df_dash[
            (pd.to_datetime(df_dash['work_date']).dt.date >= start_d) &
            (pd.to_datetime(df_dash['work_date']).dt.date <= end_d)
        ]

        d_tab_all, d_tab1, d_tab2, d_tab3 = st.tabs(["🌐 全体サマリー", "💻 商品情報", "📸 撮影", "📦 工程管理"])

        def render_category_dashboard(df_cat, category_name):
            if df_cat.empty:
                st.info(f"期間内に「{category_name}」のデータはありません。")
                return

            tot_hours = df_cat['work_hours'].sum()
            tot_other = df_cat['other_hours'].sum()
            tot_count = df_cat['valid_processed_count'].sum()
            
            avg_task_uph = round(tot_count / (tot_hours - tot_other), 2) if (tot_hours - tot_other) > 0 else 0
            avg_act_uph = round(tot_count / tot_hours, 2) if tot_hours > 0 else 0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric(f"【{category_name}】合計処理数(アパ除)", f"{tot_count:,} 点")
            k2.metric(f"【{category_name}】総稼働時間", f"{tot_hours:.2f} 時間")
            k3.metric(f"【{category_name}】作業UPH", f"{avg_task_uph:.2f}")
            k4.metric(f"【{category_name}】実質UPH", f"{avg_act_uph:.2f}")

            st.markdown("---")
            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("#### 📋 詳細作業別 集計表")
                sum_task = df_cat.groupby('task_name').agg(
                    work_hours=('work_hours', 'sum'),
                    other_hours=('other_hours', 'sum'),
                    processed_count=('processed_count', 'sum')
                ).reset_index()
                
                sum_task['作業UPH'] = sum_task.apply(lambda r: round(r['processed_count'] / (r['work_hours'] - r['other_hours']), 2) if (r['work_hours'] - r['other_hours']) > 0 else 0, axis=1)
                sum_task['実質UPH'] = sum_task.apply(lambda r: round(r['processed_count'] / r['work_hours'], 2) if r['work_hours'] > 0 else 0, axis=1)
                
                st.dataframe(sum_task.rename(columns={'task_name': '詳細作業', 'work_hours': '総稼働時間', 'processed_count': '処理数'})[['詳細作業', '総稼働時間', '処理数', '作業UPH', '実質UPH']], use_container_width=True)

            with col_right:
                st.markdown("#### 👤 担当者別 集計表")
                sum_user = df_cat.groupby('user_name').agg(
                    work_hours=('work_hours', 'sum'),
                    other_hours=('other_hours', 'sum'),
                    valid_processed_count=('valid_processed_count', 'sum')
                ).reset_index()
                sum_user = compute_summary_uph(sum_user)
                st.dataframe(sum_user.rename(columns={'user_name': '担当者名', 'work_hours': '総稼働時間', 'valid_processed_count': '処理数(アパ除)'})[['担当者名', '総稼働時間', '処理数(アパ除)', '作業UPH', '実質UPH']], use_container_width=True)

            st.markdown("#### 📈 詳細作業別 累計処理数")
            fig_task = px.bar(sum_task, x='task_name', y='processed_count', text_auto=True,
                              title=f"「{category_name}」詳細作業別 処理数",
                              labels={'task_name': '詳細作業', 'processed_count': '処理数'})
            st.plotly_chart(fig_task, use_container_width=True)

        # 1. 全体サマリー
        with d_tab_all:
            if df_dash_filtered.empty:
                st.info("選択期間内にデータがありません。")
            else:
                tot_hours_all = df_dash_filtered['work_hours'].sum()
                tot_other_all = df_dash_filtered['other_hours'].sum()
                tot_count_all = df_dash_filtered['valid_processed_count'].sum()
                
                avg_task_uph_all = round(tot_count_all / (tot_hours_all - tot_other_all), 2) if (tot_hours_all - tot_other_all) > 0 else 0
                avg_act_uph_all = round(tot_count_all / tot_hours_all, 2) if tot_hours_all > 0 else 0

                ka1, ka2, ka3, ka4 = st.columns(4)
                ka1.metric("全体 合計処理数(アパ除)", f"{tot_count_all:,} 点")
                ka2.metric("全体 総稼働時間", f"{tot_hours_all:.2f} 時間")
                ka3.metric("全体 作業UPH", f"{avg_task_uph_all:.2f}")
                ka4.metric("全体 実質UPH", f"{avg_act_uph_all:.2f}")

                st.markdown("---")
                st.markdown("#### 業務カテゴリ別 集計")
                sum_cat = df_dash_filtered.groupby('category').agg(
                    work_hours=('work_hours', 'sum'),
                    other_hours=('other_hours', 'sum'),
                    valid_processed_count=('valid_processed_count', 'sum')
                ).reset_index()
                sum_cat = compute_summary_uph(sum_cat)
                st.dataframe(sum_cat.rename(columns={'category': '業務カテゴリ', 'work_hours': '総稼働時間', 'valid_processed_count': '処理数(アパ除)'})[['業務カテゴリ', '総稼働時間', '処理数(アパ除)', '作業UPH', '実質UPH']], use_container_width=True)

                fig_all = px.bar(sum_cat, x='category', y='valid_processed_count', color='category', text_auto=True,
                                 title="業務カテゴリ別 処理数比較(アパ詳細除く)",
                                 labels={'category': '業務カテゴリ', 'valid_processed_count': '処理数'})
                st.plotly_chart(fig_all, use_container_width=True)

        # 2. 商品情報ダッシュボード
        with d_tab1:
            render_category_dashboard(df_dash_filtered[df_dash_filtered['category'] == "商品情報"], "商品情報")

        # 3. 撮影ダッシュボード
        with d_tab2:
            render_category_dashboard(df_dash_filtered[df_dash_filtered['category'] == "撮影"], "撮影")

        # 4. 工程管理ダッシュボード
        with d_tab3:
            render_category_dashboard(df_dash_filtered[df_dash_filtered['category'] == "工程管理"], "工程管理")

# ==========================================
# TAB 4: 個人・UPH分析
# ==========================================
with main_tab4:
    st.subheader("個人パフォーマンス・日次稼働確認")
    
    conn = sqlite3.connect(DB_FILE)
    df_all = pd.read_sql_query("SELECT * FROM daily_logs", conn)
    conn.close()

    if not df_all.empty:
        df_all['is_other'] = df_all['task_name'].astype(str).str.contains("その他")
        df_all['is_apa'] = df_all['task_name'].astype(str).str.contains("アパ詳細")
        
        df_all['other_hours'] = df_all.apply(lambda r: r['work_hours'] if r['is_other'] else 0, axis=1)
        df_all['valid_processed_count'] = df_all.apply(lambda r: 0 if r['is_apa'] else r['processed_count'], axis=1)

        registered_users = df_all['user_name'].unique()
        selected_user = st.selectbox("分析対象の担当者を選択", registered_users, key="anl_u")

        df_user = df_all[df_all['user_name'] == selected_user].copy()
        
        df_user['task_uph'] = df_user.apply(lambda r: 0 if r['is_other'] else round(r['processed_count'] / r['work_hours'], 2) if r['work_hours'] > 0 else 0, axis=1)
        df_user['actual_uph'] = df_user.apply(lambda r: round(r['processed_count'] / r['work_hours'], 2) if r['work_hours'] > 0 else 0, axis=1)

        st.markdown(f"#### 👤 {selected_user} さんの業務別・日別稼働内訳サマリー")
        
        df_user_cat_daily = df_user.groupby(['work_date', 'category']).agg(
            work_hours=('work_hours', 'sum'),
            other_hours=('other_hours', 'sum'),
            valid_processed_count=('valid_processed_count', 'sum')
        ).reset_index()
        
        df_user_cat_daily = compute_summary_uph(df_user_cat_daily)
        df_user_cat_daily = df_user_cat_daily.rename(columns={'work_date': '作業日', 'category': '業務カテゴリ', 'work_hours': '稼働時間', 'valid_processed_count': '処理数(アパ除)'})

        st.dataframe(df_user_cat_daily[['作業日', '業務カテゴリ', '稼働時間', '処理数(アパ除)', '作業UPH', '実質UPH']].sort_values(['作業日', '業務カテゴリ'], ascending=[False, True]), use_container_width=True)

        st.markdown(f"#### 📝 {selected_user} さんの全詳細入力履歴")
        cols_order_u = ['work_date', 'category', 'task_name', 'work_hours', 'processed_count', 'task_uph', 'actual_uph', 'notes']
        df_user_jp = df_user[cols_order_u].rename(columns=COLUMN_JAPANESE_MAP)
        st.dataframe(df_user_jp.sort_values('作業日', ascending=False), use_container_width=True)

        fig_uph = px.line(df_user_cat_daily, x='作業日', y=['作業UPH', '実質UPH'], color='業務カテゴリ', markers=True, 
                          title=f"{selected_user} さんの業務別 UPH推移",
                          labels={'value': 'UPH', 'variable': 'UPH種別'})
        st.plotly_chart(fig_uph, use_container_width=True)
    else:
        st.info("データが登録されていません。")

# ==========================================
# TAB 5: ⚙️ マスタ管理画面
# ==========================================
with main_tab5:
    st.subheader("選択肢マスタの編集")
    
    m_tab1, m_tab2 = st.tabs(["👤 業務別担当者マスタ", "📋 詳細作業マスタ"])

    # 1. 業務別担当者マスタ編集
    with m_tab1:
        col_u1, col_u2 = st.columns(2)
        
        with col_u1:
            st.markdown("**担当者の追加**")
            target_cat_u_add = st.selectbox("対象業務カテゴリ", ["商品情報", "撮影", "工程管理"], key="add_u_cat")
            new_user_name = st.text_input("担当者名を入力", key="add_u_name")
            if st.button("担当者を追加"):
                if new_user_name.strip():
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO category_user_master (category, name) VALUES (?, ?)", (target_cat_u_add, new_user_name.strip()))
                        conn.commit()
                        st.success(f"【{target_cat_u_add}】に「{new_user_name.strip()}」を追加しました。")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("その担当者は既にこの業務に登録されています。")
                    finally:
                        conn.close()
                else:
                    st.warning("名前を入力してください。")

        with col_u2:
            st.markdown("**担当者の削除**")
            target_cat_u_del = st.selectbox("対象業務カテゴリを選択", ["商品情報", "撮影", "工程管理"], key="del_u_cat")
            existing_users_del = CATEGORY_USER_MASTER.get(target_cat_u_del, [])
            
            if existing_users_del:
                delete_user_target = st.selectbox("削除する担当者を選択", existing_users_del, key="del_u_select")
                if st.button("選択した担当者を削除"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("DELETE FROM category_user_master WHERE category = ? AND name = ?", (target_cat_u_del, delete_user_target))
                    conn.commit()
                    conn.close()
                    st.success(f"【{target_cat_u_del}】から「{delete_user_target}」を削除しました。")
                    st.rerun()
            else:
                st.info("この業務に削除可能な担当者が登録されていません。")

    # 2. 詳細作業マスタ編集
    with m_tab2:
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown("**詳細作業の追加**")
            target_cat_add = st.selectbox("対象カテゴリ", ["商品情報", "撮影", "工程管理"], key="add_t_cat")
            new_task_name = st.text_input("詳細作業名を入力", key="add_t_name")
            if st.button("詳細作業を追加"):
                if new_task_name.strip():
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO task_master (category, task_name) VALUES (?, ?)", (target_cat_add, new_task_name.strip()))
                        conn.commit()
                        st.success(f"【{target_cat_add}】に「{new_task_name.strip()}」を追加しました。")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("その詳細作業名は既にこのカテゴリに登録されています。")
                    finally:
                        conn.close()
                else:
                    st.warning("作業名を入力してください。")

        with col_t2:
            st.markdown("**詳細作業の削除**")
            target_cat_del = st.selectbox("対象カテゴリを選択", ["商品情報", "撮影", "工程管理"], key="del_t_cat")
            existing_tasks_del = TASK_MASTER.get(target_cat_del, [])
            
            if existing_tasks_del:
                delete_task_target = st.selectbox("削除する詳細作業を選択", existing_tasks_del, key="del_t_select")
                if st.button("選択した詳細作業を削除"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("DELETE FROM task_master WHERE category = ? AND task_name = ?", (target_cat_del, delete_task_target))
                    conn.commit()
                    conn.close()
                    st.success(f"【{target_cat_del}】の「{delete_task_target}」を削除しました。")
                    st.rerun()
            else:
                st.info("このカテゴリに削除可能な作業が登録されていません。")

# ==========================================
# TAB 6: 📥 CSV一括取り込み
# ==========================================
with main_tab6:
    st.subheader("📥 スプレッドシート（CSV）からの一括取り込み")
    st.markdown("スプレッドシート等で管理していた過去のデータをCSV形式で一括登録できます。")
    st.markdown("""
    **【必要なCSVの列名（完全一致）】**  
    `作業日` （YYYY-MM-DD形式）, `担当者名`, `業務カテゴリ` （商品情報/撮影/工程管理）, `詳細作業`, `稼働時間(h)`, `処理数`, `備考・共有事項`
    """)
    
    uploaded_file = st.file_uploader("CSVファイルを選択", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.markdown("**アップロードデータのプレビュー（先頭5件）**")
            st.dataframe(df_upload.head())
            
            if st.button("📥 このデータで一括登録を実行する", type="primary"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                success_count = 0
                error_count = 0
                
                for _, row in df_upload.iterrows():
                    try:
                        w_date = pd.to_datetime(row['作業日']).strftime("%Y-%m-%d")
                        u_name = str(row['担当者名'])
                        cat = str(row['業務カテゴリ'])
                        t_name = str(row['詳細作業'])
                        w_hours = float(row['稼働時間(h)'])
                        p_count = int(row['処理数'])
                        notes = str(row['備考・共有事項']) if pd.notna(row['備考・共有事項']) else ""
                        
                        c.execute('''
                            INSERT INTO daily_logs (work_date, user_name, category, task_name, work_hours, processed_count, target_uph, notes)
                            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                        ''', (w_date, u_name, cat, t_name, w_hours, p_count, notes))
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                
                conn.commit()
                conn.close()
                
                if error_count == 0:
                    st.success(f"🎉 全 {success_count} 件のデータを正常に取り込みました！")
                else:
                    st.warning(f"取り込み完了: {success_count} 件成功 / {error_count} 件失敗（データ形式を確認してください）")
                
        except Exception as e:
            st.error(f"CSVの読み込み中にエラーが発生しました: {e}")
