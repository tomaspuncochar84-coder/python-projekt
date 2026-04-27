from datetime import datetime, timedelta
import csv

REFERENCE_DATE = datetime(2025, 3, 1)

PATTERN = {
    "Honza": [
        "Vol","Vol","Odp","Ran","Odp","Ran","Den","Vol","Vol","Den",
        "Vol","Vol","Vol","Vol","Mol","Mol","Vol","Odp","Ran","Den",
        "Vol","Vol","Vol","Ran","Den","Vol","Odp","Ran"
    ],
    "Martin": [
        "Mol","Mol","Vol","Odp","Ran","Den","Vol","Vol","Vol","Ran",
        "Den","Vol","Odp","Ran","Vol","Vol","Odp","Ran","Odp","Ran",
        "Den","Vol","Vol","Den","Vol","Vol","Vol","Vol"
    ],
    "Robert": [
        "Vol","Vol","Den","Vol","Vol","Vol","Vol","Mol","Mol","Vol",
        "Odp","Ran","Den","Vol","Vol","Vol","Ran","Den","Vol","Odp",
        "Ran","Vol","Vol","Odp","Ran","Odp","Ran","Den"
    ],
    "Tomáš": [
        "Vol","Vol","Ran","Den","Vol","Odp","Ran","Vol","Vol","Odp",
        "Ran","Odp","Ran","Den","Vol","Vol","Den","Vol","Vol","Vol",
        "Vol","Mol","Mol","Vol","Odp","Ran","Den","Vol"
    ]
}


def get_easter_dates(year):
    """Vrátí Velký pátek a Velikonoční pondělí"""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    easter_sunday = datetime(year, month, day)
    good_friday = easter_sunday - timedelta(days=2)
    easter_monday = easter_sunday + timedelta(days=1)
    return [
        good_friday.strftime("%d.%m."),
        easter_monday.strftime("%d.%m.")
    ]


def is_holiday(date):
    CZECH_HOLIDAYS = [
        "01.01.", "01.05.", "08.05.",
        "05.07.", "06.07.",
        "28.09.", "28.10.",
        "17.11.",
        "24.12.", "25.12.", "26.12."
    ]
    day_month = date.strftime("%d.%m.")
    year = date.year
    easter = get_easter_dates(year)
    return day_month in CZECH_HOLIDAYS or day_month in easter


def get_shift_minutes(shift, date):
    """
    Vrátí minuty pro danou směnu a datum.
    
    Mol logika:
      - Svátek (jakýkoli den): vrátí None → čeká na ruční zadání
      - Sobota (bez svátku): 771 min
      - Neděle (bez svátku): 780 min
      - Jinak: 0
    """
    weekday = date.weekday()  # 0=Po ... 6=Ne

    if shift == "Ran":
        return 481 if weekday == 1 else 457

    elif shift == "Odp":
        return 545

    elif shift == "Den":
        return 777

    elif shift == "Mol":
        if is_holiday(date):
            # Svátek (jakýkoli den) → čeká na ruční zadání
            return None
        elif weekday == 5:  # Sobota bez svátku
            return 771
        elif weekday == 6:  # Neděle bez svátku
            return 780
        else:
            return 0

    elif shift in ("D", "N", "Vol"):
        return 0

    return 0


def format_minutes(minutes):
    if minutes is None:
        return ""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02}:{mins:02}"


def format_difference(minutes):
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    hours = minutes // 60
    mins = minutes % 60
    return f"{sign}{hours:02}:{mins:02}"


def get_cycle_day(target_date):
    diff = (target_date - REFERENCE_DATE).days
    return diff % 28


def load_overrides():
    overrides = {}
    try:
        with open("overrides.csv", "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter=";")
            reader.fieldnames = [
                name.strip().replace('\ufeff', '')
                for name in reader.fieldnames
            ]

            def normalize_date(date_str):
                return datetime.strptime(date_str.strip(), "%d.%m.%Y").strftime("%d.%m.%Y")

            for row in reader:
                try:
                    key = (
                        normalize_date(row["Datum"]),
                        row["Zaměstnanec"].strip()
                    )
                    override_type = (row.get("Override") or "").strip()
                    minutes_value = (row.get("Minuty") or "").strip()

                    def parse_minutes(val):
                        if not val:
                            return None
                        if ":" in val:
                            try:
                                h, m = val.split(":")
                                return int(h) * 60 + int(m)
                            except:
                                return None
                        try:
                            return int(val)
                        except:
                            return None

                    overrides[key] = {
                        "type": override_type,
                        "minutes": parse_minutes(minutes_value)
                    }

                except KeyError:
                    print("⚠️ Špatný řádek v CSV:", row)
                    continue

    except FileNotFoundError:
        print("overrides.csv nenalezen - pokračuji bez override")

    return overrides


def get_monthly_fund(year, month):
    """Fond = 5h 21min (321 minut) × počet kalendářních dní v měsíci."""
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    return days_in_month * 321  # 5:21 = 321 minut


def generate_schedule(start_date, end_date):
    totals = {name: 0 for name in PATTERN}
    current = start_date

    with open("smenar_export.csv", "w", newline="", encoding="utf-8") as pretty_file, \
         open("smenar_backend.csv", "w", newline="", encoding="utf-8") as backend_file:

        writer = csv.writer(pretty_file, delimiter=";")
        backend_writer = csv.writer(backend_file, delimiter=";")

        writer.writerow([
            "Datum", "Cyklus den",
            "Honza", "Honza_h",
            "Martin", "Martin_h",
            "Robert", "Robert_h",
            "Tomáš", "Tomáš_h"
        ])
        backend_writer.writerow(["Datum", "Zaměstnanec", "Směna", "Minuty"])

        while current <= end_date:
            cycle_day = get_cycle_day(current)
            row = [current.strftime("%d.%m.%Y"), cycle_day + 1]

            for employee in PATTERN:
                pattern_shift = PATTERN[employee][cycle_day]

                # Svátek → vždy Vol (bez ohledu na vzor), čeká na ruční zadání
                if is_holiday(current):
                    shift = "Vol"
                    minutes_for_total = 0
                    row.append(shift)
                    row.append("")
                else:
                    shift = pattern_shift
                    minutes = get_shift_minutes(shift, current)
                    minutes_for_total = minutes if minutes is not None else 0
                    row.append(shift)
                    row.append(format_minutes(minutes) if minutes is not None else "")

                totals[employee] += minutes_for_total
                backend_writer.writerow([
                    current.strftime("%d.%m.%Y"),
                    employee,
                    shift,
                    minutes_for_total
                ])

            writer.writerow(row)
            current += timedelta(days=1)

        writer.writerow([])
        writer.writerow(["Jméno", "Odpracováno", "Fond", "Rozdíl"])

        # Roční fond: součet fondů všech měsíců v rozsahu generování
        visited_months = set()
        cur = start_date
        while cur <= end_date:
            visited_months.add((cur.year, cur.month))
            cur += timedelta(days=1)
        yearly_fund = sum(get_monthly_fund(y, m) for y, m in visited_months)

        for employee, total_minutes in totals.items():
            difference = total_minutes - yearly_fund
            writer.writerow([
                employee,
                format_minutes(total_minutes),
                format_minutes(yearly_fund),
                format_difference(difference)
            ])


def generate_actual_schedule():
    overrides = load_overrides()
    totals = {}
    daily_data = {}
    substitutes = []
    totals_by_month = {}
    employees_by_month = {}

    with open("smenar_backend.csv", "r", encoding="utf-8") as backend_file, \
         open("smenar_actual.csv", "w", newline="", encoding="utf-8") as actual_file:

        reader = csv.DictReader(backend_file, delimiter=";")
        writer = csv.writer(actual_file, delimiter=";")

        writer.writerow([
            "Datum", "Zaměstnanec", "PlannedShift", "ActualShift",
            "Výkon", "Dovolená", "Nemoc", "Školení", "ManualMinutes"
        ])

        def normalize_date(date_str):
            return datetime.strptime(date_str.strip(), "%d.%m.%Y").strftime("%d.%m.%Y")

        for row in reader:
            date_str = normalize_date(row["Datum"])
            employee = row["Zaměstnanec"].strip()
            key = (date_str, employee)
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            month = date_str.split(".")[1]

            # Inicializace struktury pro měsíc/zaměstnance
            if month not in totals_by_month:
                totals_by_month[month] = {}
            if employee not in totals_by_month[month]:
                totals_by_month[month][employee] = {
                    "vykon": 0, "dovolena": 0, "nemoc": 0, "skoleni": 0
                }

            if month not in employees_by_month:
                employees_by_month[month] = {}
            if employee not in employees_by_month[month]:
                employees_by_month[month][employee] = {}

            planned_shift = row["Směna"]
            planned_minutes = int(row["Minuty"])
            override_data = overrides.get(key)

            # --- URČENÍ SMĚNY ---
            if override_data and override_data["type"]:
                actual_shift = override_data["type"]
            else:
                actual_shift = planned_shift

            # --- VÝPOČET VÝKONU ---
            vykon = 0
            dovolena = 0
            nemoc = 0
            skoleni = 0
            has_manual = False

            # A) Ruční minuty z overrides mají absolutní přednost
            if override_data and override_data["minutes"] is not None:
                try:
                    raw = int(override_data["minutes"])
                    if raw == 0:
                        # Hodnota 0 = odemčení buňky, nulujeme ruční zápis
                        has_manual = False
                        vykon = get_shift_minutes(actual_shift, date_obj) or 0
                    else:
                        vykon = raw
                        has_manual = True
                except (ValueError, TypeError):
                    vykon = 0

            # B) Automatický výpočet podle směny
            elif actual_shift in ("Ran", "Odp", "Den"):
                vykon = get_shift_minutes(actual_shift, date_obj) or 0

            elif actual_shift == "Mol":
                mol_minutes = get_shift_minutes("Mol", date_obj)
                if mol_minutes is None:
                    # Svátek ve všední den → čeká na ruční zadání
                    vykon = 0
                else:
                    vykon = mol_minutes

            elif actual_shift == "D":
                dovolena = get_shift_minutes(planned_shift, date_obj) or 0

            elif actual_shift == "N":
                nemoc = get_shift_minutes(planned_shift, date_obj) or 0

            # --- Zjistíme jestli je Mol svátek čekající na ruční zadání ---
            mol_waiting = (
                actual_shift == "Mol"
                and not has_manual
                and get_shift_minutes("Mol", date_obj) is None
            )

            # --- PŘIDÁNÍ DO daily_data ---
            if date_str not in daily_data:
                daily_data[date_str] = []

            daily_data[date_str].append({
                "employee": employee,
                "planned": planned_shift,
                "actual": actual_shift,
                "vykon": vykon,
                "minutes": planned_minutes,
                "has_manual_minutes": has_manual,
                "mol_waiting": mol_waiting,
                "is_holiday": is_holiday(date_obj),
                "is_weekend": date_obj.weekday() >= 5
            })

            # --- PŘIDÁNÍ DO employees_by_month (každý zaměstnanec, každý den) ---
            employees_by_month[month][employee][date_str] = {
                "actual": actual_shift,
                "planned": planned_shift,
                "vykon": vykon,
                "has_manual_minutes": has_manual,
                "mol_waiting": mol_waiting,
                "is_holiday": is_holiday(date_obj),
                "is_weekend": date_obj.weekday() >= 5,
                "is_vacation": actual_shift == "D",
                "dovolena": dovolena,
                "nemoc": nemoc
            }

            # --- TOTALY ---
            if employee not in totals:
                totals[employee] = {"vykon": 0, "dovolena": 0, "nemoc": 0, "skoleni": 0}

            totals[employee]["vykon"] += vykon
            totals[employee]["dovolena"] += dovolena
            totals[employee]["nemoc"] += nemoc
            totals[employee]["skoleni"] += skoleni

            totals_by_month[month][employee]["vykon"] += vykon
            totals_by_month[month][employee]["dovolena"] += dovolena
            totals_by_month[month][employee]["nemoc"] += nemoc
            totals_by_month[month][employee]["skoleni"] += skoleni

            writer.writerow([
                date_str, employee, planned_shift, actual_shift,
                vykon, dovolena, nemoc, skoleni,
                1 if has_manual else 0
            ])

    # --- Fond pracovní doby do totals_by_month ---
    for month_str in totals_by_month:
        year = 2026
        fund = get_monthly_fund(year, int(month_str))
        for employee in totals_by_month[month_str]:
            totals_by_month[month_str][employee]["fond"] = fund

    # --- LOGIKA PRO ZÁSKOKY ---
    for date, people in daily_data.items():
        used_substitutes = set()
        for person in people:
            if person["actual"] in ("D", "N", "Šk"):
                candidates = [
                    p for p in people
                    if p["employee"] != person["employee"]
                    and p["actual"] not in ("D", "N", "Šk")
                    and p["employee"] not in used_substitutes
                    and has_enough_rest(p["employee"], date, daily_data)
                    and not did_work_yesterday(p["employee"], date, daily_data)
                    and not worked_last_days(p["employee"], date, daily_data, 6)
                    and not had_two_heavy_shifts(p["employee"], date, daily_data)
                    and p["minutes"] < 600
                ]

                volni = [p for p in candidates if p["actual"] == "Vol"]
                if volni:
                    candidates = volni

                if candidates:
                    best = min(
                        candidates,
                        key=lambda x: get_employee_workload_until(x["employee"], date, daily_data)
                    )
                    substitute = best["employee"]
                    substitute_shift = person["planned"]
                    used_substitutes.add(substitute)
                else:
                    substitute = "Leťák" if not is_weekend_str(date) else "Nikdo"
                    substitute_shift = ""

                substitutes.append({
                    "date": date,
                    "employee": person["employee"],
                    "reason": person["actual"],
                    "substitute": substitute,
                    "shift": substitute_shift
                })

    # --- ZÁPIS SOUHRNU ---
    with open("smenar_summary.csv", "w", newline="", encoding="utf-8") as summary_file:
        summary_writer = csv.writer(summary_file, delimiter=";")
        summary_writer.writerow(["Zaměstnanec", "Výkon", "Dovolená", "Nemoc", "Školení"])
        for employee, data in totals.items():
            summary_writer.writerow([
                employee,
                format_minutes(data["vykon"]),
                format_minutes(data["dovolena"]),
                format_minutes(data["nemoc"]),
                format_minutes(data["skoleni"])
            ])

    return substitutes, totals_by_month, employees_by_month


# ─── Pomocné funkce pro záskoky ───────────────────────────────────────────────

def has_enough_rest(employee, date, daily_data):
    current_date = datetime.strptime(date, "%d.%m.%Y")
    prev_date = (current_date - timedelta(days=1)).strftime("%d.%m.%Y")
    if prev_date not in daily_data:
        return True
    for p in daily_data[prev_date]:
        if p["employee"] == employee and p["minutes"] > 600:
            return False
    return True


def did_work_yesterday(employee, date, daily_data):
    current_date = datetime.strptime(date, "%d.%m.%Y")
    prev_date = (current_date - timedelta(days=1)).strftime("%d.%m.%Y")
    if prev_date not in daily_data:
        return False
    for p in daily_data[prev_date]:
        if p["employee"] == employee:
            if p["actual"] in ("Den", "Ran"):
                return True
            if p["actual"] == "Odp":
                return False
    return False


def get_employee_workload_until(employee, current_date, daily_data):
    total = 0
    current_date_dt = datetime.strptime(current_date, "%d.%m.%Y")
    for date, people in daily_data.items():
        date_dt = datetime.strptime(date, "%d.%m.%Y")
        if date_dt > current_date_dt:
            continue
        for p in people:
            if p["employee"] == employee:
                total += p["vykon"]
    return total


def is_weekend_str(date_str):
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    return date_obj.weekday() >= 5


def worked_last_days(employee, date, daily_data, days=6):
    current_date = datetime.strptime(date, "%d.%m.%Y")
    for i in range(1, days + 1):
        check_date = (current_date - timedelta(days=i)).strftime("%d.%m.%Y")
        if check_date not in daily_data:
            return False
        worked = any(
            p["employee"] == employee and p["actual"] not in ("Vol",)
            for p in daily_data[check_date]
        )
        if not worked:
            return False
    return True


def had_two_heavy_shifts(employee, date, daily_data):
    current_date = datetime.strptime(date, "%d.%m.%Y")
    heavy = ("Den", "Mol")
    count = 0
    for i in range(1, 3):
        check_date = (current_date - timedelta(days=i)).strftime("%d.%m.%Y")
        if check_date not in daily_data:
            return False
        for p in daily_data[check_date]:
            if p["employee"] == employee and p["actual"] in heavy:
                count += 1
    return count >= 2


if __name__ == "__main__":
    start = datetime(2026, 1, 1)
    end = datetime(2026, 12, 31)

    generate_schedule(start, end)
    generate_actual_schedule()

    print("Export dokončen -> smenar_export.csv + smenar_backend.csv + smenar_actual.csv")