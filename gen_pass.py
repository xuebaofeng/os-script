import random
from pypinyin import lazy_pinyin

books = [
    # ===== 金庸 =====
    "射雕英雄传","神雕侠侣","倚天屠龙记","天龙八部",
    "笑傲江湖","鹿鼎记","书剑恩仇录","碧血剑",
    "飞狐外传","雪山飞狐","侠客行","连城诀",
    "鸳鸯刀","白马啸西风",

    # ===== 古龙 =====
    "多情剑客无情剑","楚留香传奇","陆小凤传奇",
    "绝代双骄","萧十一郎","七种武器","边城浪子",
    "武林外史","大旗英雄传","欢乐英雄",
    "浣花洗剑录","英雄无泪",

    # ===== 梁羽生 =====
    "白发魔女传","七剑下天山","云海玉弓缘",
    "萍踪侠影录","大唐游侠传","冰川天女传",
    "狂侠天骄魔女","龙虎斗京华","风雷震九州",
    "还剑奇情录","散花女侠","广陵剑"
]

def to_py(text):
    return "".join(lazy_pinyin(text)).lower()

def generate():
    book = random.choice(books)
    return {
        "书名": book,
        "密码": to_py(book)
    }

if __name__ == "__main__":
    result = generate()

    print("🔥 武侠书名密码生成器（扩展版）")
    print("-" * 50)
    print("书名:", result["书名"])
    print("密码:", result["密码"])