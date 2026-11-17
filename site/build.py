"""生成全站静态页面：首页、作品页、手册、jd-lasvegas 说明页。
改文字：site/works.py；改样式：site/style.css；改手册：handbook/*.md。
用法：python -X utf8 site/build.py
原有的 hely-glass/ 和 jd-lasvegas/guide/ 不经过这个脚本。"""
import html, os, re, shutil, sys
import markdown
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from works import WORKS as ALL_WORKS, METHODS, SITES
WORKS = [w for w in ALL_WORKS if not w.get('draft')]

BASE = 'https://opc8838-hub.github.io/movie/'
GH = 'https://github.com/opc8838-hub/movie/blob/main/'
LINES = ['品牌片', '代码动效', '实拍剪辑', 'AI 短片', '设计']
E = html.escape


def write(path, text):
    p = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def fmt_dur(d):
    if d is None:
        return ''
    s = int(d)
    return f'{s // 60}:{s % 60:02d}'


def is_ext(u):
    return u.startswith(('http://', 'https://'))


def rel(pre, u):
    return u if is_ext(u) else pre + u


def page(title, desc, pre, body, active='', og=None, scripts=''):
    full = f'{title} · B2W Studio' if title else 'B2W Studio · Back 2 Work'
    img = og or 'assets/og.jpg'
    nav = ''.join(
        f'<a href="{pre}{h}"{" aria-current=\"page\"" if active == k else ""}>{k}</a>'
        for k, h in [('作品', 'index.html#works'), ('手册', 'handbook/index.html'), ('方法', 'index.html#methods')])
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
<meta name="theme-color" content="#000000">
<meta property="og:title" content="{E(full)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{BASE}{img}">
<link rel="icon" href="{pre}assets/favicon.png">
<link rel="stylesheet" href="{pre}assets/style.css">
</head>
<body>
<a class="skip" href="#main">跳到正文</a>
<header class="bar">
  <a class="home" href="{pre}index.html" aria-label="B2W Studio 首页"><img src="{pre}assets/mark-white.png" alt="" width="28" height="26"><span>STUDIO</span></a>
  <nav aria-label="主导航">{nav}</nav>
</header>
<main id="main">
{body}
</main>
{footer(pre)}
{scripts}
</body>
</html>
'''


def footer(pre):
    return f'''<div class="foot-logo" id="footLogo"><video muted playsinline preload="auto" src="{pre}assets/logo-write-light.mp4" aria-hidden="true"></video><img src="{pre}assets/logo-black.png" alt="Back 2 Work Studio" width="1244" height="280"></div>
<footer class="colophon">
  <p>部分作品是学习和练习，参考了别人的结构和节奏，个别还用了原片音乐。每支片都在作品页写明，相关权利归原作者。如需修改或移除，请<a href="https://github.com/opc8838-hub/movie/issues">在 GitHub 联系我们</a>。</p>
  <p class="r">B2W Studio · 2026<br>设计 · 视频 · 动效</p>
</footer>
<script>
(function(){{var w=document.getElementById('footLogo');if(!w)return;var v=w.querySelector('video');
if(matchMedia('(prefers-reduced-motion: reduce)').matches||!('IntersectionObserver' in window)){{w.classList.add('static');return;}}
new IntersectionObserver(function(es,o){{es.forEach(function(e){{if(e.isIntersecting){{o.disconnect();var p=v.play();if(p)p.catch(function(){{w.classList.add('static');}});}}}});}},{{threshold:.5}}).observe(v);}})();
</script>'''


def card(w):
    d = fmt_dur(w['dur']) or w['ver']
    return f'''<a class="card" href="work/{w['slug']}.html" data-line="{E(w['line'])}" data-prev="media/{w['slug']}.prev.mp4">
  <span class="media" style="aspect-ratio:{w['w']}/{w['h']}"><img src="media/{w['slug']}.jpg" alt="{E(w['title'])}封面" loading="lazy" width="{w['w']}" height="{w['h']}"></span>
  <h3>{E(w['title'])}</h3>
  <p class="meta"><span>{E(w['line'])}</span><span>{d}</span><span>{w['date']}</span><span class="tag">{E(w['tag'])}</span></p>
</a>'''


def rows(items, pre=''):
    out = ['<ul class="rows">']
    for t, s, u in items:
        tgt = ' target="_blank" rel="noopener"' if is_ext(u) else ''
        arrow = '↗' if is_ext(u) else '→'
        out.append(f'<li><a href="{rel(pre, u)}"{tgt}><b>{E(t)}</b><span>{E(s)}</span><i aria-hidden="true">{arrow}</i></a></li>')
    out.append('</ul>')
    return '\n'.join(out)


CHAPTERS = [('README', 'index', '手册首页'), ('01-workflow', '01-workflow', '01 工作流'), ('02-principles', '02-principles', '02 审美原则'),
            ('03-shot-decisions', '03-shot-decisions', '03 镜头怎么选'), ('04-templates', '04-templates', '04 模板'),
            ('05-tech', '05-tech', '05 技术规范'), ('06-delivery', '06-delivery', '06 交片与复盘'),
            ('07-ip-remake', '07-ip-remake', '07 用自己的 IP 复刻一支参考片')]


def home():
    n = len(WORKS)
    filt = '<button type="button" aria-pressed="true" data-f="">全部</button>' + ''.join(
        f'<button type="button" aria-pressed="false" data-f="{E(l)}">{E(l)}</button>' for l in LINES)
    cards = '\n'.join(card(w) for w in WORKS)
    chap = [(t, {'手册首页': '一分钟读完'}.get(t, ''), f'handbook/{h}.html') for _, h, t in CHAPTERS]
    subs = {'01 工作流': '从开工到归档，人只在三处拍板', '02 审美原则': '什么算好，交片前问自己什么', '03 镜头怎么选': '实拍、代码还是 AI',
            '04 模板': '开工单、审核、修改单，直接复制', '05 技术规范': '颜色、量参考片、踩点、去 AI 味', '06 交片与复盘': '自查清单和复盘模板',
            '07 用自己的 IP 复刻一支参考片': '人物参考包、关键帧、代码组装和逐镜报价'}
    chap = [(t, subs.get(t, s), u) for t, s, u in chap]
    body = f'''<section class="hero" id="hero" aria-label="Back 2 Work Studio">
  <video id="heroV" muted playsinline autoplay preload="auto" src="assets/logo-write-dark.mp4" aria-hidden="true"></video>
  <img class="still" src="assets/logo-white.png" alt="Back 2 Work Studio" width="1244" height="280">
  <div class="foot"><span><b>设计 · 视频 · 动效</b><br>人定故事和审美，模型把它做出来。</span><a href="#works">看作品 ↓</a></div>
</section>
<section class="sec" id="works">
  <div class="works-head"><h2 class="big">作品<sup>{n}</sup></h2><div class="filter" role="group" aria-label="按类型筛选">{filt}</div></div>
  <div class="grid" id="grid">
{cards}
  </div>
</section>
<section class="sec dark" id="how">
  <div class="how-grid">
    <div><p class="lead">错误越早发现越省钱。文字里能发现的错，不留到图上；图上能发现的错，不留到视频上。</p>
    <p>我们把每一版被否的原因都记下来，写成了一本手册：怎么开工，人在哪里拍板，哪个镜头该用实拍、代码还是 AI，交片前查什么。全部公开。</p></div>
    <div><p class="sub">工作室手册</p>{rows(chap)}</div>
  </div>
</section>
<section class="sec" id="methods">
  <div class="two">
    <div><p class="sub">方法</p>{rows(METHODS[1:])}</div>
    <div><p class="sub">网站与设计</p>{rows(SITES)}</div>
  </div>
</section>'''
    js = '''<script>
(function(){
var hero=document.getElementById('hero'),v=document.getElementById('heroV');
if(matchMedia('(prefers-reduced-motion: reduce)').matches){hero.classList.add('static');v.pause();}
else{var p=v.play();if(p)p.catch(function(){hero.classList.add('static');});}
var bs=document.querySelectorAll('.filter button'),cs=document.querySelectorAll('.card');
bs.forEach(function(b){b.addEventListener('click',function(){bs.forEach(function(x){x.setAttribute('aria-pressed',x===b);});var f=b.dataset.f;cs.forEach(function(c){c.hidden=!!f&&c.dataset.line!==f;});});});
if(matchMedia('(hover: hover)').matches&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
cs.forEach(function(c){var pv;c.addEventListener('mouseenter',function(){if(!pv){pv=document.createElement('video');pv.muted=true;pv.loop=true;pv.playsInline=true;pv.preload='auto';pv.src=c.dataset.prev;pv.setAttribute('aria-hidden','true');pv.addEventListener('playing',function(){c.classList.add('playing');});c.querySelector('.media').appendChild(pv);}var r=pv.play();if(r)r.catch(function(){});});
c.addEventListener('mouseleave',function(){if(pv){pv.pause();c.classList.remove('playing');}});});}
})();
</script>'''
    write('index.html', page('', f'B2W Studio（Back 2 Work）：设计、视频、动效。{n} 项作品和全部公开的工作方法。', '', body, scripts=js))


def work_pages():
    for w in ALL_WORKS:
        if w.get('draft'):
            stale = os.path.join(ROOT, 'work', w['slug'] + '.html')
            if os.path.exists(stale):
                os.remove(stale)
    for i, w in enumerate(WORKS):
        pre = '../'
        if w.get('parts'):
            figs = ''.join(
                f'<figure><video controls playsinline preload="none" poster="{pre}media/{p[0]}.jpg" src="{pre}media/{p[0]}.mp4" width="{p[2]}" height="{p[3]}"></video><figcaption>{E(p[1])} · {fmt_dur(p[4])}</figcaption></figure>'
                for p in w['parts'])
            top = f'<section class="parts" aria-label="全部片段">{figs}</section>'
        else:
            top = f'<section class="screen"><video controls playsinline preload="metadata" poster="{pre}media/{w["slug"]}.jpg" src="{pre}media/{w["slug"]}.mp4" width="{w["w"]}" height="{w["h"]}" style="--ar:{w["w"]}/{w["h"]};--arn:{w["w"] / w["h"]:.4f}"></video></section>'
        size = '7 段视频' if w.get('parts') else f'{fmt_dur(w["dur"])} · {w["w"]}×{w["h"]}'
        facts = [('类型', w['line']), ('性质', w['tag']), ('时间', w['date']), ('版本', w['ver']), ('规格', size)]
        fx = ''.join(f'<dt>{E(k)}</dt><dd>{E(v)}</dd>' for k, v in facts)
        how = ''
        if w['how']:
            how = '<section><h2>怎么做的</h2><ul>' + ''.join(f'<li>{E(x)}</li>' for x in w['how']) + '</ul></section>'
        learned = f'<section><h2>学到了什么</h2><p>{E(w["learned"])}</p></section>' if w['learned'] else ''
        links = ''
        if w['links']:
            ls = ''.join(f'<a href="{rel(pre, u)}"{" target=\"_blank\" rel=\"noopener\"" if is_ext(u) else ""}>{E(t)}{" ↗" if is_ext(u) else " →"}</a>' for t, u in w['links'])
            links = f'<p class="more">{ls}</p>'
        prv = WORKS[i - 1]
        nxt = WORKS[(i + 1) % len(WORKS)]
        info_first = bool(w.get('parts'))
        body = f'''{"" if info_first else top}
<section class="info{" first" if info_first else ""}">
  <div><h1>{E(w['title'])}</h1><p class="en">{E(w['en'])}</p><dl class="facts">{fx}</dl></div>
  <div class="body">
    <p class="summary">{E(w['summary'])}</p>
    {how}
    {learned}
    <section class="note"><h2>注明</h2><p>{E(w['note'])}</p></section>
    {links}
  </div>
</section>
{top if info_first else ""}
<nav class="pager" aria-label="上一个和下一个作品"><a href="{prv['slug']}.html"><small>← 上一个</small>{E(prv['title'])}</a><a href="{nxt['slug']}.html"><small>下一个 →</small>{E(nxt['title'])}</a></nav>'''
        write(f'work/{w["slug"]}.html', page(w['title'], w['summary'], pre, body, active='作品', og=f'media/{w["slug"]}.jpg'))


def slugify(value, sep):
    t = value.strip().lower()
    t = re.sub(r'[^\w一-鿿\- ]', '', t)
    return t.replace(' ', '-')


def md_html(text, link_fn):
    h = markdown.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists', 'toc'],
                          extension_configs={'toc': {'slugify': slugify}})
    h = h.replace('<table>', '<div class="tb"><table>').replace('</table>', '</table></div>')
    h = re.sub(r'<li>\[ \]\s*', '<li class="task">', h)
    return re.sub(r'href="([^"]+)"', lambda m: 'href="%s"' % link_fn(html.unescape(m[1])), h)


def handbook_link(u):
    if is_ext(u) or u.startswith('#'):
        return u
    p, _, a = u.partition('#')
    a = '#' + a if a else ''
    if p == '../README.md':
        return '../jd-lasvegas/guide/' + a
    if p == '../hely-glass/README.md':
        return '../hely-glass/' + a
    if p == 'README.md':
        return 'index.html' + a
    if p.endswith('.md'):
        return p[:-3] + '.html' + a
    return u


def handbook():
    for src, out, label in CHAPTERS:
        text = open(os.path.join(ROOT, 'handbook', src + '.md'), encoding='utf-8').read()
        title = re.match(r'#\s+(.*)', text).group(1)
        toc = '<nav class="toc" aria-label="手册目录"><ol>' + ''.join(
            f'<li><a href="{h}.html"{" aria-current=\"page\"" if h == out else ""}>{E(t)}</a></li>' for _, h, t in CHAPTERS) + '</ol></nav>'
        body = f'<div class="doc-wrap">{toc}<article class="doc">{md_html(text, handbook_link)}</article></div>'
        write(f'handbook/{out}.html', page(title, 'B2W Studio 工作室手册：' + title, '../', body, active='手册'))


def jd_page():
    text = open(os.path.join(ROOT, 'jd-lasvegas', 'README.md'), encoding='utf-8').read()

    def link(u):
        if is_ext(u) or u.startswith('#'):
            return u
        if u.rstrip('/') == 'guide':
            return 'guide/'
        return GH + 'jd-lasvegas/' + u
    body = f'<div class="doc-wrap" style="grid-template-columns:minmax(0,1fr)"><article class="doc"><p><a href="guide/">打开可播放的学习页 →</a></p>{md_html(text, link)}</article></div>'
    write('jd-lasvegas/index.html', page('拉斯维加斯歌词 MV 复盘', '方法复盘、执行方案和脚本', '../', body, active='方法'))


shutil.copy(os.path.join(HERE, 'style.css'), os.path.join(ROOT, 'assets', 'style.css'))
home()
work_pages()
handbook()
jd_page()
write('.nojekyll', '')
print('built', len(WORKS), 'works')
