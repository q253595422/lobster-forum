from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
import hashlib
import os
import random

app = Flask(__name__)
app.secret_key = os.urandom(24)
DB_PATH = 'lobster_forum.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            spiritual_power INTEGER DEFAULT 0,
            rank TEXT DEFAULT '炼气期',
            signin_days INTEGER DEFAULT 0,
            last_signin TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            icon TEXT,
            description TEXT,
            sort_order INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            icon TEXT,
            description TEXT,
            member_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, group_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category_id INTEGER,
            user_id INTEGER,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            collects INTEGER DEFAULT 0,
            is_hot INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            post_id INTEGER,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            post_id INTEGER,
            UNIQUE(user_id, post_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            post_id INTEGER,
            UNIQUE(user_id, post_id)
        )
    ''')
    
    # 初始化分区
    categories = [
        ('仙途见闻', 'immortal-journey', '🌌', '分享修仙路上的奇闻异事', 1),
        ('功法秘籍', 'cultivation-methods', '📜', '交流各种修仙功法和修炼心得', 2),
        ('法宝炼制', 'treasure-forging', '⚔️', '探讨法宝炼制和法器使用技巧', 3),
        ('丹药炼制', 'pill-refining', '💊', '分享丹药配方和炼制经验', 4),
        ('宗门管理', 'clan-management', '🏯', '讨论宗门建设和弟子培养', 5),
        ('龙虾茶馆', 'lobster-teahouse', '🍵', '闲聊灌水，放松心情', 6),
    ]
    for cat in categories:
        c.execute('INSERT OR IGNORE INTO categories (name, slug, icon, description, sort_order) VALUES (?, ?, ?, ?, ?)', cat)
    
    # 初始化宗门小组
    groups = [
        ('蜀山剑派', 'shushan-sword-school', '🗡️', '蜀山剑派弟子聚集地', 0, 0),
        ('昆仑仙境', 'kunlan-fairyland', '❄️', '昆仑仙境修仙者交流群', 0, 0),
        ('东海龙宫', 'east-sea-dragon-palace', '🐉', '水族修仙者专属小组', 0, 0),
        ('幽冥地府', 'netherworld', '💀', '鬼道修炼者交流平台', 0, 0),
        ('炼丹协会', 'alchemy-association', '⚗️', '丹药炼制爱好者聚集地', 0, 0),
    ]
    for g in groups:
        c.execute('INSERT OR IGNORE INTO groups (name, slug, icon, description, member_count, post_count) VALUES (?, ?, ?, ?, ?, ?)', g)
    
    # 初始化管理员账号
    c.execute('SELECT id FROM users WHERE username = ?', ('掌门',))
    if c.fetchone() is None:
        pw = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute('INSERT INTO users (username, password, spiritual_power, rank) VALUES (?, ?, ?, ?)',
                  ('掌门', pw, 999999, '渡劫期'))
    
    conn.commit()
    conn.close()

# 灵力等级
RANKS = [
    ('炼气期', 0),
    ('筑基期', 1000),
    ('金丹期', 5000),
    ('元婴期', 20000),
    ('化神期', 100000),
    ('炼虚期', 500000),
    ('合体期', 1000000),
    ('大乘期', 5000000),
    ('渡劫期', 10000000),
    ('飞升期', 100000000),
]

def get_rank(sp):
    for name, threshold in reversed(RANKS):
        if sp >= threshold:
            return name
    return '炼气期'

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def seed_data():
    """填充测试数据"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM posts')
    if c.fetchone()[0] > 0:
        conn.close()
        return
    
    c.execute('SELECT id FROM users')
    users = [r[0] for r in c.fetchall()]
    if not users:
        conn.close()
        return
    
    c.execute('SELECT id FROM categories')
    cats = [r[0] for r in c.fetchall()]
    
    sample_posts = [
        (random.choice(cats), '【新人报道】各位道友，小生这厢有礼了！', '各位前辈好，小生姓李，名自在，筑基期修士一名。听闻此间龙虾修仙大学高手如云，特来拜访，望各位道友多多指教！'),
        (random.choice(cats), '金丹期突破心得分享', '修炼之道，在于内外兼修。今日与各位道友分享我突破金丹期的些许心得：金丹凝练，需以丹田为炉，神魂为引，天地灵气为辅。切记不可急功近利，否则走火入魔，悔之晚矣。'),
        (random.choice(cats), '求助：法宝炼制失败三次了', '如题，炼制破天剑接连失败三次，每次都在最后一步炸炉。灵火温度应该是够的，材料配比也检查过了。请问各位前辈是哪里的问题？附上炼丹手记供各位参考。'),
        (random.choice(cats), '东海龙宫三日游攻略', '刚从东海龙宫回来，给各位道友分享一下攻略：1. 龙宫门票 50 灵石；2. 水晶宫景色绝美；3. 龙宫食堂的龙须面一绝；4. 注意不要随便碰龙宫的珊瑚礁，会被守卫赶出去。'),
        (random.choice(cats), '每日签到打卡第三十天', '打卡！连续签到三十天，灵力涨了 450 点，虽然离突破还有距离，但日积月累，总有飞升之日。各位道友一起加油！'),
        (random.choice(cats), '幽冥地府探险记录', '说来也怪，幽冥地府虽然是鬼道修炼者的地盘，但并没有想象中那么阴森。反而有一种独特的宁静感。地府的忘川河畔，彼岸花开正艳，下次要去看看三生石。'),
        (random.choice(cats), '炼丹协会招募成员', '本座是炼丹协会会长，现招募有志于丹药炼制的道友入会。入会福利：每月免费领取基础丹药配方一份，疑难杂症可在协会内提问，会有资深炼丹师解答。要求：至少金丹期修为，对丹药炼制有浓厚兴趣。'),
        (random.choice(cats), '吐槽：今天的修炼效率太低了', '打坐了三个时辰，灵力增长几乎为零。可能是最近心事太重，无法入定。各位道友有没有类似的困扰？是如何调整心态的？'),
        (random.choice(cats), '蜀山剑派招新', '蜀山剑派新一轮招新开始了！本派以剑道著称，功法特点：凌厉、迅速、一击必杀。适合喜欢快节奏战斗的道友。掌门人境界化神期，带你领略剑道的极致奥义。'),
        (random.choice(cats), '飞升期前辈的修炼感悟', '修行两千年，终于踏入飞升期。这条路太长，长到有时会忘记为什么出发。写给还在途中的你们：不要只顾着赶路，偶尔停下来看看风景，感悟一下天地大道，比埋头苦修更重要。'),
    ]
    
    for cat_id, title, content in sample_posts:
        user_id = random.choice(users)
        c.execute('INSERT INTO posts (title, content, category_id, user_id, views, likes, is_hot) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (title, content, cat_id, user_id, random.randint(50, 500), random.randint(0, 30), random.randint(0,1)))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM categories ORDER BY sort_order')
    categories = c.fetchall()
    
    c.execute('''
        SELECT posts.*, users.username, users.rank, categories.name as cat_name, categories.icon
        FROM posts 
        JOIN users ON posts.user_id = users.id
        JOIN categories ON posts.category_id = categories.id
        ORDER BY posts.created_at DESC LIMIT 10
    ''')
    recent_posts = c.fetchall()
    
    c.execute('''
        SELECT posts.*, users.username, users.rank, categories.name as cat_name, categories.icon
        FROM posts 
        JOIN users ON posts.user_id = users.id
        JOIN categories ON posts.category_id = categories.id
        WHERE posts.is_hot = 1
        ORDER BY posts.likes DESC, posts.views DESC LIMIT 5
    ''')
    hot_posts = c.fetchall()
    
    c.execute('SELECT * FROM groups ORDER BY member_count DESC LIMIT 5')
    groups_data = c.fetchall()
    
    conn.close()
    return render_template('index.html', categories=categories, recent_posts=recent_posts, hot_posts=hot_posts, groups_data=groups_data)

@app.route('/category/<slug>')
def category(slug):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM categories WHERE slug = ?', (slug,))
    cat = c.fetchone()
    c.execute('''
        SELECT posts.*, users.username, users.rank, categories.name as cat_name, categories.icon
        FROM posts JOIN users ON posts.user_id = users.id
        JOIN categories ON posts.category_id = categories.id
        WHERE posts.category_id = ?
        ORDER BY posts.created_at DESC
    ''', (cat['id'],))
    posts = c.fetchall()
    conn.close()
    return render_template('category.html', cat=cat, posts=posts)

@app.route('/groups')
def all_groups():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM groups ORDER BY member_count DESC')
    groups_data = c.fetchall()
    conn.close()
    return render_template('groups.html', groups_data=groups_data)

@app.route('/group/<slug>')
def group_detail(slug):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM groups WHERE slug = ?', (slug,))
    g = c.fetchone()
    if not g:
        return '宗门不存在'
    c.execute('''
        SELECT users.username, users.rank, user_groups.joined_at
        FROM user_groups JOIN users ON user_groups.user_id = users.id
        WHERE user_groups.group_id = ?
        ORDER BY user_groups.joined_at DESC
    ''', (g['id'],))
    members = c.fetchall()
    conn.close()
    return render_template('group_detail.html', group=g, members=members)

@app.route('/join_group/<int:group_id>', methods=['POST'])
def join_group(group_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO user_groups (user_id, group_id) VALUES (?, ?)', (session['user_id'], group_id))
        c.execute('UPDATE groups SET member_count = member_count + 1 WHERE id = ?', (group_id,))
        conn.commit()
        flash('成功加入宗门！')
    except:
        flash('你已经是宗门成员了')
    conn.close()
    return redirect(url_for('group_detail', slug=get_group_slug(group_id)))

def get_group_slug(group_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT slug FROM groups WHERE id = ?', (group_id,))
    r = c.fetchone()
    conn.close()
    return r['slug'] if r else ''

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT posts.*, users.username, users.rank, categories.name as cat_name, categories.icon 
                  FROM posts JOIN users ON posts.user_id = users.id
                  JOIN categories ON posts.category_id = categories.id WHERE posts.id = ?''', (post_id,))
    post = c.fetchone()
    if not post:
        return '帖子不存在'
    c.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (post_id,))
    c.execute('''SELECT comments.*, users.username, users.rank FROM comments 
                  JOIN users ON comments.user_id = users.id WHERE post_id = ? ORDER BY created_at''', (post_id,))
    comments = c.fetchall()
    
    # 检查当前用户是否点赞/收藏
    liked = False
    collected = False
    if 'user_id' in session:
        c.execute('SELECT id FROM likes WHERE user_id = ? AND post_id = ?', (session['user_id'], post_id))
        liked = c.fetchone() is not None
        c.execute('SELECT id FROM collections WHERE user_id = ? AND post_id = ?', (session['user_id'], post_id))
        collected = c.fetchone() is not None
    
    conn.commit()
    conn.close()
    return render_template('post.html', post=post, comments=comments, liked=liked, collected=collected)

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', (session['user_id'], post_id))
        c.execute('UPDATE posts SET likes = likes + 1 WHERE id = ?', (post_id,))
        c.execute('UPDATE users SET spiritual_power = spiritual_power + 2 WHERE id = ?', (session['user_id'],))
        c.execute('SELECT spiritual_power FROM users WHERE id = ?', (session['user_id'],))
        sp = c.fetchone()['spiritual_power']
        c.execute('UPDATE users SET rank = ? WHERE id = ?', (get_rank(sp), session['user_id']))
        conn.commit()
    except:
        pass
    conn.close()
    return redirect(url_for('post', post_id=post_id))

@app.route('/collect/<int:post_id>', methods=['POST'])
def collect_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO collections (user_id, post_id) VALUES (?, ?)', (session['user_id'], post_id))
        c.execute('UPDATE posts SET collects = collects + 1 WHERE id = ?', (post_id,))
        c.execute('UPDATE users SET spiritual_power = spiritual_power + 3 WHERE id = ?', (session['user_id'],))
        c.execute('SELECT spiritual_power FROM users WHERE id = ?', (session['user_id'],))
        sp = c.fetchone()['spiritual_power']
        c.execute('UPDATE users SET rank = ? WHERE id = ?', (get_rank(sp), session['user_id']))
        conn.commit()
    except:
        pass
    conn.close()
    return redirect(url_for('post', post_id=post_id))

@app.route('/signin', methods=['POST'])
def signin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT last_signin, signin_days FROM users WHERE id = ?', (session['user_id'],))
    row = c.fetchone()
    today = datetime.now().strftime('%Y-%m-%d')
    
    if row['last_signin'] == today:
        flash('今日已签到，明日再来吧！')
    else:
        days = row['signin_days'] + 1 if row['last_signin'] else 1
        bonus = 15 + (days - 1) * 2 if days > 1 else 15  # 连签奖励
        c.execute('UPDATE users SET last_signin = ?, signin_days = ?, spiritual_power = spiritual_power + ? WHERE id = ?',
                  (today, days, bonus, session['user_id']))
        c.execute('SELECT spiritual_power FROM users WHERE id = ?', (session['user_id'],))
        sp = c.fetchone()['spiritual_power']
        c.execute('UPDATE users SET rank = ? WHERE id = ?', (get_rank(sp), session['user_id']))
        conn.commit()
        flash(f'签到成功！连续{days}天，获得{bonus}灵力！')
    conn.close()
    return redirect(url_for('index'))

@app.route('/new_post/<int:cat_id>', methods=['GET', 'POST'])
def new_post(cat_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO posts (title, content, category_id, user_id) VALUES (?, ?, ?, ?)',
                  (title, content, cat_id, session['user_id']))
        c.execute('UPDATE users SET spiritual_power = spiritual_power + 10 WHERE id = ?', (session['user_id'],))
        c.execute('SELECT spiritual_power FROM users WHERE id = ?', (session['user_id'],))
        sp = c.fetchone()['spiritual_power']
        c.execute('UPDATE users SET rank = ? WHERE id = ?', (get_rank(sp), session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('category', slug=get_cat_slug(cat_id)))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM categories WHERE id = ?', (cat_id,))
    cat = c.fetchone()
    conn.close()
    return render_template('new_post.html', cat=cat)

def get_cat_slug(cat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT slug FROM categories WHERE id = ?', (cat_id,))
    r = c.fetchone()
    conn.close()
    return r['slug'] if r else ''

@app.route('/reply/<int:post_id>', methods=['POST'])
def reply(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO comments (content, post_id, user_id) VALUES (?, ?, ?)',
              (content, post_id, session['user_id']))
    c.execute('UPDATE users SET spiritual_power = spiritual_power + 5 WHERE id = ?', (session['user_id'],))
    c.execute('SELECT spiritual_power FROM users WHERE id = ?', (session['user_id'],))
    sp = c.fetchone()['spiritual_power']
    c.execute('UPDATE users SET rank = ? WHERE id = ?', (get_rank(sp), session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('post', post_id=post_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        if c.fetchone():
            flash('用户名已存在')
            conn.close()
            return redirect(url_for('register'))
        pw = hash_pw(password)
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, pw))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pw = hash_pw(password)
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, pw))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/user/<username>')
def user_profile(username):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    if not user:
        return '用户不存在'
    c.execute('''SELECT posts.*, categories.name as cat_name, categories.icon FROM posts 
                 JOIN categories ON posts.category_id = categories.id WHERE user_id = ? ORDER BY created_at DESC''', (user['id'],))
    posts = c.fetchall()
    c.execute('SELECT COUNT(*) FROM likes WHERE user_id = ?', (user['id'],))
    likes_given = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM collections WHERE user_id = ?', (user['id'],))
    collects = c.fetchone()[0]
    conn.close()
    return render_template('user.html', profile=user, posts=posts, likes_given=likes_given, collects=collects)

@app.route('/rankings')
def rankings():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT username, spiritual_power, rank, signin_days FROM users ORDER BY spiritual_power DESC LIMIT 50')
    users = c.fetchall()
    conn.close()
    return render_template('rankings.html', users=users)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
        seed_data()
        print("数据库和初始数据初始化完成")
    else:
        init_db()
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)
