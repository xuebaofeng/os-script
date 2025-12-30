import cnlunar
from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta

name = "父亲"
lunar_month = 10
lunar_day = 8
years = 10
remind_days_before = 7  # 提前提醒天数

cal = Calendar()
start_year = datetime.now().year

for year in range(start_year, start_year + years):
    found = False
    for month in range(1, 13):
        for day in range(1, 32):
            try:
                dt = datetime(year, month, day)
            except ValueError:
                continue
            lunar = cnlunar.Lunar(dt)
            if lunar.lunarMonth == lunar_month and lunar.lunarDay == lunar_day:
                solar_date = dt.date()
                print(f"✅ {year} 农历正月初十 -> 公历 {solar_date}")

                e = Event()
                e.name = f"🎂 {name} 农历生日"
                e.begin = solar_date
                e.make_all_day()

                # 使用 DisplayAlarm 正确添加提前提醒
                alarm = DisplayAlarm(trigger=timedelta(days=-remind_days_before),
                                     display_text=f"提醒: 🎂 {name} 农历生日")
                e.alarms.append(alarm)

                cal.events.add(e)
                found = True
                break
        if found:
            break

with open("calendar.ics", "w", encoding="utf-8") as f:
    f.writelines(cal)

print("✅ ICS 文件生成完成：calendar.ics")
