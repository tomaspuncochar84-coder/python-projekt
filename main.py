def pridej_vydaj():
    castka = input("Kolik jsi utratil?")
    popis = input("Za co to bylo?")

    with open("vydaje.txt", "a") as soubor:
        soubor.write(f"{castka} Kč - {popis}\n")
    print("Uloženo!")

def zobraz_vydaje():
    try:
        with open("vydaje.txt", "r") as soubor:
            print("\n--- Tvoje výdaje ---")
            print(soubor.read())
    except FileNotFoundError:
        print("Zatím nemáš žádné výdaje.")
while True:
    print("\n1 - Přidat výdaj")
    print("2 - Zobrazit výdaje")
    print("3 - Konec")

    volba = input("Vyber: ")

    if volba == "1":
        pridej_vydaj()
    elif volba == "2":
        zobraz_vydaje()
    elif volba == "3":
        print("Čau")
        break
    else:
        print("Neplatná volba")