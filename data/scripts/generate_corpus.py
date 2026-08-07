"""
Generate the synthetic operator corpus from catalog.py.

Every document renders from the single canonical catalogue, so 150+ files
cannot contradict each other on prices, zones or dates.

Run:  python data/generate_corpus.py
Out:  data/corpus/operator/**/*.md
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import catalog as C  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "corpus" / "operator"
DEN = "ден."


def front(doc_id: str, title: str, lang: str, year: int, family: str) -> str:
    status = "in_force" if year == C.CURRENT_YEAR else "superseded"
    return (
        "---\n"
        f"doc_id: {doc_id}\n"
        f"title: {title}\n"
        "source: operator\n"
        "authority: operator\n"
        f"family: {family}\n"
        f"language: {lang}\n"
        f"effective_date: {year}-01-01\n"
        f"status: {status}\n"
        "---\n\n"
    )


written: list[Path] = []


def w(name: str, body: str) -> None:
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    written.append(p)


def money(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".") if v == int(v) else f"{v:.2f}".replace(".", ",")


# ───────────────────────────────────────────────────────────── price lists
def gen_price_lists() -> None:
    for plan in C.PLANS:
        for y in C.YEARS:
            gb, pr = plan.data_gb[y], plan.price[y]
            data_mk = f"{gb} GB" if gb else f"неограничен со ФУП од {plan.fup_gb} GB"
            data_en = f"{gb} GB" if gb else f"unlimited, fair use {plan.fup_gb} GB"
            prev = (
                f"\nВо {y-1} година цената изнесуваше {money(plan.price[y-1])} {DEN}.\n"
                if y > C.YEARS[0]
                else "\n"
            )

            w(
                f"price/op-cenovnik-{plan.code.lower()}-{y}-mk.md",
                front(
                    f"op-cenovnik-{plan.code.lower()}-{y}",
                    f"Ценовник — {plan.name} ({y})",
                    "mk",
                    y,
                    "price",
                )
                + f"""# {plan.name}
## Ценовник за {y} година

Важи од 1 јануари {y}. Цените се во денари со вклучен ДДВ.

| Ставка | Вредност |
|---|---|
| Месечна претплата | **{money(pr)} {DEN}** |
| Интернет во домашна мрежа | {data_mk} |
| Разговори кон домашни мрежи | {plan.minutes} |
| SMS кон домашни мрежи | {plan.sms} |
| Максимална брзина | до {plan.speed_mbps} Mbps |
{prev}
## Што се случува по потрошена квота

Брзината се намалува на {C.FUP['throttle_kbps']} kbps до крајот на пресметковниот период.
Не се наплаќа автоматска доплата по MB. Наплата по MB се врши само ако е рачно
овозможена опцијата „Продолжи со полна брзина" во Мој Вардар.

## Дополнителни пакети за интернет

| Пакет | Количина | Важност | Цена |
|---|---|---|---|
"""
                + "\n".join(
                    f"| Додаток {a['gb']} GB | {a['gb']} GB | {a['days']} дена | {money(a['price'][y])} {DEN} |"
                    for a in C.DATA_ADDONS
                )
                + f"""

## Промена на пакет

Промена во повисок пакет важи веднаш, со пропорционална пресметка. Промена во понизок
пакет важи од следниот период и за време на минималниот договорен период е можна само
ако новата претплата не е под {C.CONTRACT['downgrade_floor_pct']}% од првичната.
""",
            )

            w(
                f"price/op-pricelist-{plan.code.lower()}-{y}-en.md",
                front(
                    f"op-cenovnik-{plan.code.lower()}-{y}",
                    f"Price list — {plan.name} ({y})",
                    "en",
                    y,
                    "price",
                )
                + f"""# {plan.name}
## Price list for {y}

Effective 1 January {y}. Prices in MKD including VAT.

| Item | Value |
|---|---|
| Monthly fee | **{money(pr)} MKD** |
| Domestic data | {data_en} |
| Calls to domestic networks | {plan.minutes} |
| SMS to domestic networks | {plan.sms} |
| Maximum speed | up to {plan.speed_mbps} Mbps |

## After the allowance is used

Speed is reduced to {C.FUP['throttle_kbps']} kbps for the remainder of the billing period.
No per-MB charge is applied automatically. Per-MB billing occurs only if the
subscriber explicitly enables "Continue at full speed" in My Vardar.

## Data add-ons

| Add-on | Volume | Validity | Price |
|---|---|---|---|
"""
                + "\n".join(
                    f"| Add-on {a['gb']} GB | {a['gb']} GB | {a['days']} days | {money(a['price'][y])} MKD |"
                    for a in C.DATA_ADDONS
                )
                + f"""

## Changing plan

Upgrades apply immediately with pro-rata billing. Downgrades apply from the next period,
and during the minimum term are permitted only if the new fee is at least
{C.CONTRACT['downgrade_floor_pct']}% of the original.
""",
            )


# ───────────────────────────────────────────────────────────── roaming
def gen_roaming() -> None:
    for y in C.YEARS:
        rows_mk, rows_en = [], []
        for z in C.ZONES[1:]:
            rows_mk.append(
                f"| {z.name_mk} | {z.regime_mk} | {money(z.mb[y])} {DEN}/MB | {money(z.out_min[y])} {DEN}/мин |"
            )
            rows_en.append(
                f"| {z.name_en} | {z.regime_en} | {money(z.mb[y])} MKD/MB | {money(z.out_min[y])} MKD/min |"
            )
        packs_mk = "\n".join(
            f"| {p['code']} | {[z.name_mk for z in C.ZONES if z.key==p['zone']][0]} | {p['gb']} GB | {p['days']} дена | {money(p['price'][y])} {DEN} |"
            for p in C.ROAMING_PACKS
        )
        packs_en = "\n".join(
            f"| {p['code']} | {[z.name_en for z in C.ZONES if z.key==p['zone']][0]} | {p['gb']} GB | {p['days']} days | {money(p['price'][y])} MKD |"
            for p in C.ROAMING_PACKS
        )

        w(
            f"roaming/op-roaming-{y}-mk.md",
            front(f"op-roaming-{y}", f"Роаминг зони и цени ({y})", "mk", y, "roaming")
            + f"""# Роаминг зони, режими и цени — {y}

Република Северна Македонија не е членка на Европската унија ниту на Европскиот
економски простор. Затоа Регулативата (ЕУ) 2022/612 за роаминг, која го воведува
принципот „роаминг како дома", не се применува директно на нашите претплатници.

Патувањето во Грција не е исто како патувањето во Србија, иако обете се во Европа.

| Зона | Режим | Интернет | Појдовна минута |
|---|---|---|---|
"""
            + "\n".join(rows_mk)
            + f"""

## Зона 1 — Западен Балкан
{C.ZONES[1].countries_mk}.
Основа: {C.ZONES[1].basis_mk}. Домашната квота важи без доплата.

## Зона 2 — ЕУ и ЕЕА
{C.ZONES[2].countries_mk}.
Основа: {C.ZONES[2].basis_mk}. Ова не е роаминг како дома.

## Зона 3 — Останат свет
{C.ZONES[3].countries_mk}.
Основа: {C.ZONES[3].basis_mk}.

**Внимание.** Турција и Швајцарија често погрешно се сметаат за дел од европскиот
режим. Ниту една не е членка на ЕУ или ЕЕА, ниту е дел од Регионалниот договор за
Западен Балкан. Обете се наплаќаат по Зона 3.

## Роаминг пакети

| Код | Зона | Количина | Важност | Цена |
|---|---|---|---|---|
{packs_mk}

За Зона 1 не постои пакет затоа што не е потребен.

## Контрола на трошоци
Автоматски месечен лимит од {money(C.FUP['roaming_monthly_cap_mkd'])} {DEN} за податоци во
Зона 2 и Зона 3. При 100% пренесувањето се прекинува додека не се потврди со
`ROAMING OK` на 1300. Итните повици не се засегнати.
""",
        )

        w(
            f"roaming/op-roaming-{y}-en.md",
            front(f"op-roaming-{y}", f"Roaming zones and rates ({y})", "en", y, "roaming")
            + f"""# Roaming zones, regimes and rates — {y}

North Macedonia is not a member of the European Union or the European Economic Area.
Regulation (EU) 2022/612, which establishes Roam Like At Home, therefore does not
apply directly to our subscribers.

Travelling to Greece is not the same as travelling to Serbia, even though both are
in Europe.

| Zone | Regime | Data | Outgoing minute |
|---|---|---|---|
"""
            + "\n".join(rows_en)
            + f"""

## Zone 1 — Western Balkans
{C.ZONES[1].countries_en}. Basis: {C.ZONES[1].basis_en}. Domestic allowance applies with no surcharge.

## Zone 2 — EU and EEA
{C.ZONES[2].countries_en}. Basis: {C.ZONES[2].basis_en}. This is not Roam Like At Home.

## Zone 3 — Rest of world
{C.ZONES[3].countries_en}. Basis: {C.ZONES[3].basis_en}.

**Note.** Turkey and Switzerland are frequently assumed to fall under the European
regime. Neither is an EU or EEA member, and neither is party to the Western Balkans
Regional Roaming Agreement. Both are billed at Zone 3 rates.

## Roaming packs

| Code | Zone | Volume | Validity | Price |
|---|---|---|---|---|
{packs_en}

There is no pack for Zone 1 because none is needed.
""",
        )


# ───────────────────────────────────────────────────────── troubleshooting
TS_MK = {
    "no-service": [
        "Исклучете и вклучете го режимот за летање. Ова присилува повторна регистрација на мрежата и решава мнозинството случаи.",
        "Рестартирајте го уредот.",
        "Проверете дали е избран автоматски избор на мрежа. Рачно заклучена мрежа е честа причина по враќање од странство.",
        "Извадете ја и вратете ја SIM картичката, проверете за оштетување на контактите.",
        "Проверете дали има пријавен прекин во вашето подрачје.",
        "Тестирајте ја картичката во друг уред. Ако работи таму, проблемот е во уредот.",
    ],
    "no-calls": [
        "Проверете дали има сигнал и дали бројот е внесен во целосен формат.",
        "Проверете забрана за појдовни повици со `*#33#`.",
        "Проверете го статусот на сметката. Суспензија поради неплаќање ги блокира појдовните повици но ги дозволува дојдовните.",
        "Ако проблемот е само кон странство, проверете дали е овозможена меѓународна телефонија.",
        "Ако повиците паѓаат по неколку секунди, проверете го VoLTE статусот.",
    ],
    "no-sms": [
        "Проверете го центарот за пораки. За Вардар Мобиле бројот е +389 70 100 100.",
        "Ако сте користеле друга картичка во уредот, овој број може да остане од претходниот оператор. Ова е најчестата причина.",
        "Проверете слободна меморија на картичката и уредот.",
        "Кратките броеви и услугите со додадена вредност не се вклучени во квотата.",
    ],
    "no-data": [
        "Проверете дали е вклучен мобилниот интернет и исклучен режимот за штедење податоци.",
        "Проверете ја состојбата на квотата со `*123#`.",
        "Проверете ги APN поставките.",
        "Ако сте во странство, проверете дали е овозможен податочен роаминг во поставките на уредот. Ова е одделно од дозволата кај операторот.",
        "Ресетирајте ги мрежните поставки. Ова ги брише зачуваните Wi-Fi лозинки.",
    ],
    "slow-data": [
        "Тестирајте на отворено, не во внатрешност со дебели ѕидови.",
        "Споредете во различно време. Меѓу 19 и 23 часот мрежата е најоптоварена.",
        f"Проверете дали квотата е потрошена. По потрошена квота брзината е {C.FUP['throttle_kbps']} kbps.",
        "Проверете дали уредот е на 4G или 5G. Заклучување на 3G дава значително пониски брзини.",
        "Проверете дали е активен VPN. VPN намалува брзина за 10 до 40%.",
        "Ако брзината е под 25% од договорената подолго од 3 дена, поднесете рекламација.",
    ],
    "roaming-fail": [
        "Проверете дали роамингот е овозможен кај операторот со `*123#`.",
        "Проверете дали е овозможен податочен роаминг во поставките на уредот. Тоа се две различни дозволи и обете мора да се вклучени.",
        f"Проверете дали е достигнат месечниот лимит од {money(C.FUP['roaming_monthly_cap_mkd'])} {DEN}. Ако е, испратете ROAMING OK на 1300.",
        "Обидете се со рачен избор на мрежа. Некои странски мрежи немаат договор со операторот.",
        "За нови претплатници во првите три месеци роамингот бара депозит.",
    ],
    "voicemail": [
        "Активација со `*111#`, слушање на 1211.",
        "Ресетирање на PIN со SMS со текстот VMPIN на 1300.",
        "Пораките се чуваат 30 дена, максимум 20 зачувани, до 3 минути по порака.",
    ],
}
TS_EN = {
    "no-service": [
        "Toggle airplane mode. This forces re-registration and resolves the majority of cases.",
        "Restart the device.",
        "Check that automatic network selection is enabled. A manually locked network is a common cause after returning from abroad.",
        "Remove and reinsert the SIM, checking the contacts for damage.",
        "Check whether an outage is reported in your area.",
        "Test the SIM in another device. If it works there, the problem is the device.",
    ],
    "no-calls": [
        "Check signal and that the number is dialled in full format.",
        "Check outgoing call barring with `*#33#`.",
        "Check account status. Suspension for non-payment blocks outgoing calls but allows incoming.",
        "If only international calls fail, check whether international dialling is enabled.",
        "If calls drop after a few seconds, check VoLTE status.",
    ],
    "no-sms": [
        "Check the message centre number. For Vardar Mobile it is +389 70 100 100.",
        "If you have used another operator's SIM in this device, that number may have persisted. This is the most common cause.",
        "Check free memory on SIM and device.",
        "Short codes and premium services are not included in the allowance.",
    ],
    "no-data": [
        "Check that mobile data is on and data saver is off.",
        "Check your remaining allowance with `*123#`.",
        "Check APN settings.",
        "If abroad, check that data roaming is enabled in device settings. This is separate from the operator-side permission.",
        "Reset network settings. This clears saved Wi-Fi passwords.",
    ],
    "slow-data": [
        "Test outdoors rather than indoors behind thick walls.",
        "Compare at different times. The network is busiest between 19:00 and 23:00.",
        f"Check whether the allowance is exhausted. After that, speed is {C.FUP['throttle_kbps']} kbps.",
        "Check whether the device is on 4G or 5G. Locking to 3G gives materially lower speeds.",
        "Check for an active VPN. A VPN reduces throughput by 10 to 40%.",
        "If speed is below 25% of the contracted rate for more than 3 days, file a complaint.",
    ],
    "roaming-fail": [
        "Check that roaming is enabled on the account with `*123#`.",
        "Check that data roaming is enabled in device settings. These are two separate permissions and both must be on.",
        f"Check whether the monthly cap of {money(C.FUP['roaming_monthly_cap_mkd'])} MKD has been reached. If so, send ROAMING OK to 1300.",
        "Try manual network selection. Some foreign networks have no agreement with the operator.",
        "New subscribers require a deposit for roaming during the first three months.",
    ],
    "voicemail": [
        "Activate with `*111#`, listen on 1211.",
        "Reset the PIN by texting VMPIN to 1300.",
        "Messages are kept 30 days, maximum 20 stored, up to 3 minutes each.",
    ],
}


def gen_troubleshooting() -> None:
    y = C.CURRENT_YEAR
    for key, mk, en in C.SYMPTOMS:
        steps_mk = "\n".join(f"{i}. {s}" for i, s in enumerate(TS_MK[key], 1))
        steps_en = "\n".join(f"{i}. {s}" for i, s in enumerate(TS_EN[key], 1))
        w(
            f"support/op-ts-{key}-mk.md",
            front(f"op-ts-{key}", f"Техничка поддршка — {mk}", "mk", y, "support")
            + f"# {mk}\n\n## Чекори за решавање\n\n{steps_mk}\n\n"
            "## Ако ниту еден чекор не помага\n\nЈавете се на 1300 или отворете барање во Мој Вардар. "
            "Наведете го моделот на уредот, точното време кога проблемот започнал, и дали се јавува на едно место или насекаде.\n",
        )
        w(
            f"support/op-ts-{key}-en.md",
            front(f"op-ts-{key}", f"Technical support — {en}", "en", y, "support")
            + f"# {en}\n\n## Resolution steps\n\n{steps_en}\n\n"
            "## If none of the steps help\n\nCall 1300 or open a request in My Vardar. State the device model, "
            "the exact time the problem started, and whether it happens in one location or everywhere.\n",
        )


# ───────────────────────────────────────────────────────────── campaigns
def gen_campaigns() -> None:
    for key, mk, en, y in C.CAMPAIGNS:
        plan = C.PLANS[hash(key) % len(C.PLANS)]
        disc = 15 + (hash(key) % 4) * 5
        months = 6 + (hash(key) % 3) * 3
        w(
            f"campaigns/op-campaign-{key}-mk.md",
            front(f"op-campaign-{key}", f"Услови за кампања — {mk}", "mk", y, "campaign")
            + f"""# {mk}
## Услови за учество

Кампањата важи за нови претплатници и за постојни претплатници кои обновуваат договор
во периодот на траење.

| Ставка | Вредност |
|---|---|
| Пакет во понудата | {plan.name} |
| Попуст на месечна претплата | {disc}% |
| Времетраење на попустот | првите {months} месеци |
| Редовна претплата по попустот | {money(plan.price[y])} {DEN} |
| Минимален договорен период | {C.CONTRACT['min_term_months']} месеци |

## Ограничувања

Попустот не се кумулира со семејни и бизнис попусти. По истекот на промотивниот период
се применува редовната цена од важечкиот Ценовник, за што претплатникот се известува
30 дена однапред.

Предвременото раскинување во промотивниот период го активира надоместот од Општите
услови, зголемен за износот на искористениот попуст.

Кампањата не важи за пренос на број од оператор со кој е склучен договор пократок од
6 месеци.
""",
        )
        w(
            f"campaigns/op-campaign-{key}-en.md",
            front(f"op-campaign-{key}", f"Campaign terms — {en}", "en", y, "campaign")
            + f"""# {en}
## Participation terms

Available to new subscribers and to existing subscribers renewing during the campaign period.

| Item | Value |
|---|---|
| Plan | {plan.name} |
| Discount on monthly fee | {disc}% |
| Discount duration | first {months} months |
| Standard fee afterwards | {money(plan.price[y])} MKD |
| Minimum term | {C.CONTRACT['min_term_months']} months |

## Restrictions

The discount does not stack with family or business discounts. After the promotional
period the standard price list applies, with 30 days' notice.

Early termination during the promotional period triggers the standard fee plus the
value of the discount already received.
""",
        )


# ───────────────────────────────────────────────────────────── devices
def gen_devices() -> None:
    y = C.CURRENT_YEAR
    for d in C.DEVICES:
        m = round(d["price"] / d["months"])
        w(
            f"devices/op-device-{d['model'].lower().replace(' ', '-')}-mk.md",
            front(
                f"op-device-{d['model'].lower().replace(' ','-')}",
                f"Уред на рати — {d['model']}",
                "mk",
                y,
                "device",
            )
            + f"""# {d['model']} на рати

| Ставка | Вредност |
|---|---|
| Цена на уредот | {money(d['price'])} {DEN} |
| Период на отплата | {d['months']} месеци |
| Месечна рата | {money(m)} {DEN} |
| Каматна стапка | 0% |

Ратата се наплаќа заедно со месечната претплата, како посебна ставка на истата сметка.

Уредот е во сопственост на претплатникот од моментот на преземање. Операторот задржува
право на побарување за неплатените рати, но не на уредот.

Предвремена отплата е можна во секое време без надомест.

При раскинување на договорот преостанатите рати доспеваат веднаш во целост, заедно со
неамортизираниот дел од субвенцијата ако таква била одобрена.

Минималниот договорен период е еднаков на периодот на отплата, односно {d['months']} месеци.
""",
        )
        w(
            f"devices/op-device-{d['model'].lower().replace(' ', '-')}-en.md",
            front(
                f"op-device-{d['model'].lower().replace(' ','-')}",
                f"Device instalments — {d['model']}",
                "en",
                y,
                "device",
            )
            + f"""# {d['model']} on instalments

| Item | Value |
|---|---|
| Device price | {money(d['price'])} MKD |
| Instalment period | {d['months']} months |
| Monthly instalment | {money(m)} MKD |
| Interest rate | 0% |

The instalment is billed alongside the monthly fee as a separate line on the same invoice.

The device belongs to the subscriber from collection. The operator retains a claim on
unpaid instalments but not on the device.

Early settlement is available at any time without penalty.

On contract termination all remaining instalments fall due immediately, together with
the unamortised portion of any subsidy.
""",
        )


# ───────────────────────────────────────────────────────────── procedures
PROC_MK = {
    "apn": (
        "APN поставки",
        [
            ("Име", "Vardar Internet"),
            ("APN", "internet.vardar.mk"),
            ("Корисничко име", "празно"),
            ("Лозинка", "празно"),
            ("MCC", "294"),
            ("MNC", "04"),
            ("Тип на автентикација", "нема"),
            ("Тип на APN", "default,supl"),
            ("Протокол", "IPv4/IPv6"),
        ],
    ),
    "esim": (
        "Активација на eSIM",
        [
            ("Чекор 1", "Проверете дека уредот поддржува eSIM и не е заклучен за друга мрежа"),
            ("Чекор 2", "Побарајте eSIM преку Мој Вардар или во салон, добивате QR код"),
            ("Чекор 3", "Поставки, Мобилна мрежа, Додај мобилен план"),
            ("Чекор 4", "Скенирајте го QR кодот, не го затворајте екранот"),
            ("Чекор 5", "Означете го профилот како основен за податоци и повици"),
            ("Чекор 6", "Рестартирајте го уредот"),
        ],
    ),
    "volte": (
        "Активација на VoLTE",
        [
            ("Услов 1", "Уредот поддржува VoLTE и е одобрен за мрежата"),
            ("Услов 2", "Картичката е издадена по 2019 година"),
            ("Услов 3", "Услугата е активирана на сметката"),
            ("Активација", "Поставки, Мобилна мрежа, VoLTE повици"),
        ],
    ),
    "wifi-calling": (
        "Wi-Fi Calling",
        [
            ("Наплата дома", "како вообичаен домашен повик"),
            ("Наплата во странство преку Wi-Fi", "по домашна тарифа, не по роаминг тарифа"),
            (
                "Итни повици",
                "користат адреса регистрирана во Мој Вардар, ажурирајте ја при преселба",
            ),
        ],
    ),
    "device-move": (
        "Пренос на број на нов уред",
        [
            ("Физичка картичка", "извадете и вметнете во новиот уред"),
            ("eSIM", "побарајте нов QR код пред да го избришете стариот профил"),
            ("QR код", "може да се употреби само еднаш"),
            ("Прв нов код во 12 месеци", "бесплатен"),
        ],
    ),
    "compatibility": (
        "Компатибилност на уреди",
        [
            ("Фреквенции 4G", "B1, B3, B7, B20"),
            ("Фреквенции 5G", "n1, n3, n78"),
            ("Заклучени уреди", "уред купен кај друг оператор може да бара одблокирање"),
            ("Провера на IMEI", "*#06#, потоа проверка во Мој Вардар"),
        ],
    ),
}


def gen_procedures() -> None:
    y = C.CURRENT_YEAR
    for key, mk, en in C.PROCEDURES:
        title, rows = PROC_MK[key]
        tbl = "\n".join(f"| {k} | {v} |" for k, v in rows)
        w(
            f"procedures/op-proc-{key}-mk.md",
            front(f"op-proc-{key}", f"Постапка — {mk}", "mk", y, "procedure")
            + f"# {mk}\n\n| Поле | Вредност |\n|---|---|\n{tbl}\n\n"
            "Ако постапката не успее, јавете се на 1300 со моделот на уредот и верзијата на оперативниот систем.\n",
        )
        w(
            f"procedures/op-proc-{key}-en.md",
            front(f"op-proc-{key}", f"Procedure — {en}", "en", y, "procedure")
            + f"# {en}\n\n| Field | Value |\n|---|---|\n{tbl}\n\n"
            "If the procedure fails, call 1300 with your device model and OS version.\n",
        )


# ───────────────────────────────────────────────────────────── misc families
def gen_misc() -> None:
    y = C.CURRENT_YEAR
    ct = C.CONTRACT

    for lang, t in (
        ("mk", "Договорен период и раскинување"),
        ("en", "Contract term and termination"),
    ):
        ex_plan = C.PLANS[1]
        rem, fee = 14, 14 * ex_plan.price[y] * ct["early_fee_pct"] / 100
        body_mk = f"""# {t}

## Минимален период
Стандардно {ct['min_term_months']} месеци за договори со субвенциониран уред или промотивна цена.
Договор без уред и без промоција може да се склучи без минимален период, со претплата повисока за 15%.

## Отказен рок
{ct['notice_days']} дена од приемот на барањето.

## Предвремено раскинување
Надоместот се пресметува како: **преостанати цели месеци × {ct['early_fee_pct']}% од месечната претплата**.

Пример: {ex_plan.name}, претплата {money(ex_plan.price[y])} {DEN}, раскинување со {rem} преостанати месеци.
{rem} × {money(ex_plan.price[y])} × 0,{ct['early_fee_pct']} = **{money(fee)} {DEN}**

Ако е земен субвенциониран уред, дополнително се плаќа неамортизираниот дел од субвенцијата,
пресметан линеарно.

## Раскинување без надомест
Измена на условите на штета на претплатникот, смрт на претплатникот, трајно преселување
надвор од покриеност, прекин по вина на операторот подолг од 15 дена во месец, и
раскинување во рокот од {ct['cooloff_days']} дена за договори склучени на далечина.

## Пренос на број не е раскинување
Преносот на бројот кај друг оператор не го раскинува договорот. Надоместот за предвремено
раскинување останува да се плаќа. Ова е најчестата причина за жалби.
"""
        body_en = f"""# {t}

## Minimum term
{ct['min_term_months']} months by default for contracts with a subsidised device or promotional pricing.
A contract with no device and no promotion can be taken with no minimum term, at a fee 15% higher.

## Notice period
{ct['notice_days']} days from receipt of the request.

## Early termination
The fee is **remaining whole months × {ct['early_fee_pct']}% of the monthly fee**.

Example: {ex_plan.name} at {money(ex_plan.price[y])} MKD, terminated with {rem} months remaining.
{rem} × {money(ex_plan.price[y])} × 0.{ct['early_fee_pct']} = **{money(fee)} MKD**

If a subsidised device was taken, the unamortised portion of the subsidy is also due,
calculated on a straight-line basis.

## Termination without penalty
Terms changed to the subscriber's detriment, death of the subscriber, permanent relocation
outside the coverage area, an operator-caused outage exceeding 15 days in a month, and
termination within the {ct['cooloff_days']}-day cooling-off period for distance contracts.

## Number portability is not termination
Porting your number to another operator does not terminate the contract. The early
termination fee still applies. This is the single most common source of complaints.
"""
        w(
            f"contract/op-contract-{y}-{lang}.md",
            front(f"op-contract-{y}", t, lang, y, "contract")
            + (body_mk if lang == "mk" else body_en),
        )

    fup = C.FUP
    w(
        f"fairuse/op-fairuse-{y}-mk.md",
        front(f"op-fairuse-{y}", "Политика за фер користење", "mk", y, "fairuse")
        + f"""# Политика за фер користење

Политиката постои за да спречи користење кое отстапува значително од вообичаеното и им
штети на другите корисници. Таа не е механизам за дополнителна наплата.

## Домашна мрежа
За пакетот со неограничен интернет границата е **{fup['xl_domestic_gb']} GB** месечно.
По надминување брзината се намалува на {fup['throttle_kbps']} kbps до крајот на периодот,
**без доплата**. Повиците, SMS и итните служби остануваат неизменети.

## Роаминг во Зона 1
Домашната квота важи во целост. Дополнително се применува критериум за стабилна врска
со Северна Македонија: ако во четири последователни месеци претплатникот има претежно
присуство во роаминг и потрошувачката во роаминг е поголема од домашната, се испраќа
предупредување. Ако состојбата не се промени во 14 дена, може да се примени доплата
од 0,45 {DEN} по MB.

Оваа одредба спречува трајно користење на македонска картичка како основна врска во
друга земја. Не се однесува на вообичаени патувања, сезонска работа или студирање до
четири месеци.

## Известување
SMS при 80% и при 100% од секоја граница, со објаснување што следи.
""",
    )
    w(
        f"fairuse/op-fairuse-{y}-en.md",
        front(f"op-fairuse-{y}", "Fair use policy", "en", y, "fairuse")
        + f"""# Fair use policy

The policy exists to prevent usage that departs substantially from normal patterns and
harms other users. It is not a mechanism for additional billing.

## Domestic
For the unlimited plan the threshold is **{fup['xl_domestic_gb']} GB** per month. Beyond it,
speed is reduced to {fup['throttle_kbps']} kbps for the rest of the period, **with no surcharge**.
Calls, SMS and emergency services are unaffected.

## Zone 1 roaming
The full domestic allowance applies. A stable-link test also applies: if over four
consecutive months the subscriber is predominantly roaming and roaming consumption
exceeds domestic consumption, a warning is issued. If unchanged after 14 days, a
surcharge of 0.45 MKD per MB may apply.

This prevents permanent use of a Macedonian SIM as a primary connection in another
country. It does not affect ordinary travel, seasonal work or study of up to four months.
""",
    )

    w(
        f"billing/op-billing-{y}-mk.md",
        front(f"op-billing-{y}", "Сметки, рекламации и права", "mk", y, "billing")
        + f"""# Сметки, рекламации и права на потрошувачите

## Пресметковен период
Календарски месец. Сметката се издава до 8-ми во наредниот месец, со рок за плаќање
не пократок од 15 дена. Детална спецификација бесплатно во Мој Вардар за последните
6 месеци; печатена 150 {DEN}.

## Зошто сметката е повисока од вообичаено
1. Роаминг во Зона 2 или 3 без активиран пакет
2. Пропорционална пресметка при промена на пакет во средината на периодот
3. Повици кон кратки броеви и услуги со додадена вредност
4. Рата за уред што започнала во тековниот период
5. Претплата на дигитални услуги активирана преку SMS
6. Истек на промотивен попуст
7. Меѓународни повици од дома, што не е исто со роаминг

## Рекламација
Се поднесува во рок од **30 дена** од приемот на сметката. Операторот одговара во рок
од **15 дена**. Спорниот износ не се наплаќа додека трае постапката; неспорниот дел се
плаќа редовно.

Ако рекламацијата е одбиена или нема одговор во рок, претплатникот може да се обрати
до Агенцијата за електронски комуникации во рок од 15 дена.

## Прекин и надомест
Прекин подолг од 48 часа по вина на операторот дава право на пропорционален надомест.
Прекин подолг од 15 дена во месец дава право на раскинување без надомест.
""",
    )
    w(
        f"billing/op-billing-{y}-en.md",
        front(f"op-billing-{y}", "Billing, complaints and consumer rights", "en", y, "billing")
        + """# Billing, complaints and consumer rights

## Billing period
Calendar month. Invoices are issued by the 8th of the following month with a payment
term of no less than 15 days. Itemised detail is free in My Vardar for the last 6 months.

## Why a bill is higher than usual
1. Roaming in Zone 2 or 3 without an active pack
2. Pro-rata billing after a mid-period plan change
3. Calls to short codes and premium services
4. A device instalment starting this period
5. Digital subscriptions activated by SMS
6. A promotional discount expiring
7. International calls from home, which are not the same as roaming

## Complaints
Filed within **30 days** of receiving the invoice. The operator responds within **15 days**.
The disputed amount is not collected while the case is open.

If rejected or unanswered, the subscriber may escalate to the Agency for Electronic
Communications within 15 days.
""",
    )

    esc_rows = [
        ("Пријава за кражба на уред или SIM", "Итно, бара идентификација", "Веднаш кон 1300"),
        ("Сомнеж за злоупотреба или измама", "Безбедносен инцидент", "Кон тим за безбедност"),
        ("Барање за туѓа сметка", "Заштита на податоци", "Одбиј, не пренасочувај"),
        ("Рекламација во формална постапка", "Правен рок тече", "Кон референтот"),
        ("Податоци за сообраќај од трето лице", "Само по судски налог", "Кон правна служба"),
        ("Смрт на претплатник", "Бара документација", "Кон салон"),
        ("Закана или итен случај", "Надвор од опсегот", "Упати кон 112"),
        ("Отпис на долг над 5.000 ден.", "Надвор од овластување", "Кон наплата"),
    ]
    w(
        f"escalation/op-escalation-{y}-mk.md",
        front(
            f"op-escalation-{y}",
            "Политика за ескалација кон човечки оператор",
            "mk",
            y,
            "escalation",
        )
        + "# Политика за ескалација\n\nДигиталниот асистент не смее самостојно да ги обработува следните барања.\n\n"
        "| Ситуација | Причина | Насока |\n|---|---|---|\n"
        + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in esc_rows)
        + "\n\nЗа сите останати барања асистентот може да одговори, но секое дејство што менува состојба "
        "бара потврда од претплатникот, а неповратните дејства бараат одобрение од човечки оператор.\n",
    )
    w(
        f"escalation/op-escalation-{y}-en.md",
        front(f"op-escalation-{y}", "Escalation policy", "en", y, "escalation")
        + "# Escalation policy\n\nThe assistant must not handle the following autonomously.\n\n"
        "| Situation | Reason | Route |\n|---|---|---|\n"
        "| Reported device or SIM theft | Urgent, requires identification | Immediately to 1300 |\n"
        "| Suspected fraud or misuse | Security incident | Security team |\n"
        "| Request concerning another account | Data protection | Refuse, do not route |\n"
        "| Complaint already in formal process | Legal clock running | Case handler |\n"
        "| Third-party traffic data | Court order only | Legal |\n"
        "| Death of subscriber | Requires documentation | Retail store |\n"
        "| Threat or emergency | Out of scope | Direct to 112 |\n"
        "| Debt write-off above 5,000 MKD | Beyond authority | Collections |\n\n"
        "For everything else the assistant may answer, but any state-changing action requires "
        "subscriber confirmation, and irreversible actions require human approval.\n",
    )

    w(
        f"network/op-network-{y}-mk.md",
        front(f"op-network-{y}", "Управување со сообраќајот и покриеност", "mk", y, "network")
        + f"""# Управување со сообраќајот, покриеност и што значи „неограничено"

## Начело
Операторот го третира сообраќајот еднакво, без дискриминација или мешање, независно од
испраќачот, примачот, содржината или апликацијата.

## Кога се применуваат мерки
Само привремено при исклучителна преоптовареност, за исполнување на законски обврски,
или за зачувување на интегритетот и безбедноста на мрежата. Мерките се пропорционални
и траат само колку што е потребно.

## Што влијае на реалната брзина
Оддалеченост од базната станица и препреки; број на корисници на ќелијата, со врв меѓу
19 и 23 часот; способности на уредот; внатрешно наспроти надворешно, каде разликата може
да надмине 60%; достапност на 5G во подрачјето; и оптовареност на оддалечениот сервер.

## Што значи „неограничено"
Дека нема ограничување на количината и нема доплата по надминување на прагот. Не значи
неограничена брзина: по {fup['xl_domestic_gb']} GB брзината е {fup['throttle_kbps']} kbps до крајот на периодот.
""",
    )
    w(
        f"network/op-network-{y}-en.md",
        front(f"op-network-{y}", "Traffic management and coverage", "en", y, "network")
        + f"""# Traffic management, coverage, and what "unlimited" means

## Principle
Traffic is treated equally without discrimination or interference, regardless of sender,
recipient, content or application.

## When measures apply
Only temporarily during exceptional congestion, to meet legal obligations, or to preserve
network integrity and security. Measures are proportionate and last only as long as needed.

## What affects real-world speed
Distance from the base station and obstructions; number of users on the cell, peaking
between 19:00 and 23:00; device capability; indoor versus outdoor, where the difference
can exceed 60%; 5G availability in the area; and remote server load.

## What "unlimited" means
No volume cap and no surcharge past a threshold. It does not mean unlimited speed: past
{fup['xl_domestic_gb']} GB the rate is {fup['throttle_kbps']} kbps for the remainder of the period.
""",
    )


# ───────────────────────────────────────────────────────────── SIM, security, portability, FAQ
def gen_rest() -> None:
    y = C.CURRENT_YEAR

    for key, mk, en in C.SECURITY:
        w(
            f"security/op-sec-{key}-mk.md",
            front(f"op-sec-{key}", f"Безбедност — {mk}", "mk", y, "security")
            + f"# {mk}\n\n"
            + {
                "lost-sim": "Веднаш јавете се на 1300 од кој било број, или блокирајте преку Мој Вардар.\n\n"
                "Блокирањето е моментално. Од тој момент не одговарате за понатамошниот сообраќај. "
                "**За сообраќајот пред блокирањето одговара претплатникот**, што е причината зошто "
                "пријавувањето треба да биде веднаш.\n\nПри кражба препорачуваме и пријава во полиција. "
                "Записникот е потребен за спор околу сообраќај остварен пред блокирањето.\n\n"
                "Нова картичка со ист број се издава во салон со лична карта, за 300 ден.\n",
                "block-sim": "Блокирање по IMEI бара полициски записник и доказ за сопственост. Блокираниот "
                "IMEI не може да се користи во ниту една домашна мрежа. Одблокирањето бара писмено барање "
                "од лицето што го пријавило.\n\nIMEI се проверува со `*#06#`. Запишете го сега, додека го "
                "имате уредот.\n",
                "pin-reset": "Фабричкиот PIN е 1234 и препорачуваме да го смените. По три погрешни обиди "
                "картичката бара PUK, достапен во Мој Вардар, на пакувањето, или во салон со лична карта.\n\n"
                "**По десет погрешни PUK обиди картичката трајно се блокира** и бара замена. Нема начин "
                "да се врати.\n",
                "fraud": "Ако забележите повици што не сте ги направиле, сметки за услуги што не сте ги "
                "активирале, или ако престанете да примате повици без причина, што може да укаже на "
                "неовластен пренос на бројот, јавете се веднаш на 1300 и побарајте привремено блокирање.\n\n"
                "Операторот **никогаш** не бара PIN, лозинка или SMS код преку телефон, e-mail или порака.\n",
            }[key],
        )
        w(
            f"security/op-sec-{key}-en.md",
            front(f"op-sec-{key}", f"Security — {en}", "en", y, "security")
            + f"# {en}\n\nCall 1300 immediately from any number, or block via My Vardar.\n\n"
            "Blocking is immediate. From that moment you are not liable for further traffic. "
            "**You remain liable for traffic before the block**, which is why reporting must be immediate.\n",
        )

    w(
        f"sim/op-sim-{y}-mk.md",
        front(f"op-sim-{y}", "SIM и eSIM — издавање, замена, Мулти SIM", "mk", y, "sim")
        + f"""# SIM и eSIM

## Замена

| Причина | Цена | Рок |
|---|---|---|
| Технички дефект во првите 12 месеци | бесплатно | веднаш |
| Оштетување по вина на корисникот | 300 {DEN} | веднаш во салон |
| Губење или кражба | 300 {DEN} | веднаш во салон |
| Промена на формат (физички ↔ eSIM) | бесплатно | до 2 часа |

При замена бројот и сите услуги остануваат непроменети.

## eSIM
QR кодот може да се употреби само еднаш. Ако профилот се избрише, потребен е нов код,
кој за прв пат во 12 месеци е бесплатен. При промена на уред профилот не се пренесува
автоматски: побарајте нов код **пред** да го избришете стариот.

## Мулти SIM
До три дополнителни картички со ист број и споделена квота, за 149 {DEN} месечно по
картичка. Повиците ѕвонат на сите уреди истовремено.
""",
    )
    w(
        f"sim/op-sim-{y}-en.md",
        front(f"op-sim-{y}", "SIM and eSIM", "en", y, "sim")
        + """# SIM and eSIM

Replacement is free for technical defects within 12 months, 300 MKD for user damage,
loss or theft, and free when changing format between physical SIM and eSIM.

An eSIM QR code can be used only once. If the profile is deleted a new code is needed,
free once per 12 months. When changing devices the profile does not transfer
automatically: request a new code **before** deleting the old profile.

Multi SIM provides up to three additional SIMs sharing one number and allowance, at
149 MKD per month each.
""",
    )

    w(
        f"portability/op-portability-{y}-mk.md",
        front(f"op-portability-{y}", "Пренос на број кај друг оператор", "mk", y, "portability")
        + """# Пренос на број

## Право
Секој претплатник има право да го задржи бројот при премин кај друг оператор. Правото
не може да се ограничи со договорна одредба.

## Постапка
Барањето се поднесува кај **новиот** оператор, не кај постојниот. Потребна е лична карта
и бројот што се пренесува. Постапката трае **еден работен ден**. Прекинот при преминот
трае најмногу 4 часа и се врши ноќе.

## Кога може да се одбие
Бројот не постои или не е активен; податоците не се совпаѓаат; бројот е веќе во постапка;
бројот е блокиран поради пријавена кражба.

**Неплатена сметка не е основа за одбивање.** Долгот останува побарување на стариот оператор.

## Обврските остануваат
Преносот **не го раскинува** договорот. Ако сте во минималниот договорен период,
надоместот за предвремено раскинување останува да се плаќа. Ова е најчестата причина
за жалби: преносот на број и раскинувањето се две различни работи.
""",
    )
    w(
        f"portability/op-portability-{y}-en.md",
        front(f"op-portability-{y}", "Number portability", "en", y, "portability")
        + """# Number portability

The request is submitted to the **new** operator, not the current one, and completes
within one working day. An unpaid bill is **not** grounds for refusal; the debt remains
a claim of the old operator.

Porting does **not** terminate the contract. If you are within the minimum term, the
early termination fee still applies. Porting and terminating are two different things,
and confusing them is the most common source of complaints.
""",
    )

    faq_mk = {
        "plans": [
            ("Кои пакети ги нудите?", "S, M, L и XL, од 599 до 1.799 ден. месечно."),
            (
                "Што се случува ако ја потрошам квотата?",
                f"Брзината се намалува на {C.FUP['throttle_kbps']} kbps до крајот на месецот, без автоматска доплата.",
            ),
            (
                "Може ли да преминам на понизок пакет?",
                f"Да, од следниот месец. Во минималниот период само ако новата претплата не е под {C.CONTRACT['downgrade_floor_pct']}% од првичната.",
            ),
        ],
        "roaming": [
            (
                "Дали роамингот е бесплатен во Европа?",
                "Не насекаде. Во Западен Балкан да. Во ЕУ и ЕЕА се наплаќа по ограничени цени бидејќи Северна Македонија не е членка на ЕУ.",
            ),
            (
                "Турција е во Европа, значи Зона 2?",
                "Не. Турција не е во ЕУ ниту во ЕЕА и не е дел од регионалниот договор. Турција е Зона 3.",
            ),
            (
                "Како да избегнам висока сметка?",
                "Активирајте роаминг пакет пред патување и оставете го месечниот лимит вклучен.",
            ),
        ],
        "contract": [
            (
                "Колку чини предвременото раскинување?",
                f"Преостанати месеци × {C.CONTRACT['early_fee_pct']}% од претплатата, плус неамортизираната субвенција за уредот.",
            ),
            (
                "Ако го пренесам бројот, престанува ли договорот?",
                "Не. Тоа се две различни работи и надоместот останува.",
            ),
        ],
        "network": [
            (
                "Зошто ми е побавен интернетот навечер?",
                "Меѓу 19 и 23 часот мрежата е најоптоварена.",
            ),
            (
                "Дали неограничено значи неограничена брзина?",
                f"Не. Значи дека нема доплата. По {C.FUP['xl_domestic_gb']} GB брзината е {C.FUP['throttle_kbps']} kbps.",
            ),
        ],
        "billing": [
            (
                "Колку време имам за рекламација?",
                "30 дена од приемот на сметката. Одговор во рок од 15 дена.",
            ),
            (
                "Зошто ми е сметката повисока?",
                "Најчесто роаминг без пакет, пропорционална пресметка по промена на пакет, или рата за уред.",
            ),
        ],
        "sim": [
            (
                "Ја изгубив картичката?",
                "Јавете се на 1300 веднаш. За сообраќајот пред блокирањето одговарате вие.",
            ),
            (
                "Може ли ист број на повеќе уреди?",
                "Да, преку Мулти SIM, до три дополнителни картички.",
            ),
        ],
        "technical": [
            (
                "Немам сигнал, што прво?",
                "Исклучете и вклучете го режимот за летање, потоа рестартирајте.",
            ),
            ("SMS не се испраќаат?", "Проверете го центарот за пораки: +389 70 100 100."),
        ],
        "devices": [
            ("Има ли камата на рати?", "Не, каматната стапка е 0%."),
            ("Може ли предвремена отплата?", "Да, во секое време без надомест."),
        ],
        "account": [
            ("Како ја проверувам квотата?", "`*123#` или Мој Вардар."),
            ("Може ли детална сметка?", "Да, бесплатно во Мој Вардар за последните 6 месеци."),
        ],
    }
    for key, mk_t, en_t in C.FAQ_CATEGORIES:
        qs = faq_mk.get(key, [])
        w(
            f"faq/op-faq-{key}-mk.md",
            front(f"op-faq-{key}", f"Најчести прашања — {mk_t}", "mk", y, "faq")
            + f"# Најчести прашања: {mk_t}\n\n"
            + "\n\n".join(f"**{q}**\n\n{a}" for q, a in qs)
            + "\n",
        )
        w(
            f"faq/op-faq-{key}-en.md",
            front(f"op-faq-{key}", f"FAQ — {en_t}", "en", y, "faq")
            + f"# FAQ: {en_t}\n\nSee the corresponding Macedonian FAQ and the detailed policy documents.\n",
        )


# ═════════════════════════════════════════════════════════════════════════
# Added: the two families that create real volume AND the hardest retrieval
# problem. 42 near-identical country sheets force the retriever to
# discriminate between documents that differ only by country and zone.
# ═════════════════════════════════════════════════════════════════════════

COUNTRY_NAMES = {
    "MK": ("Северна Македонија", "North Macedonia"),
    "AL": ("Албанија", "Albania"),
    "BA": ("Босна и Херцеговина", "Bosnia and Herzegovina"),
    "XK": ("Косово", "Kosovo"),
    "ME": ("Црна Гора", "Montenegro"),
    "RS": ("Србија", "Serbia"),
    "AT": ("Австрија", "Austria"),
    "BE": ("Белгија", "Belgium"),
    "BG": ("Бугарија", "Bulgaria"),
    "HR": ("Хрватска", "Croatia"),
    "CY": ("Кипар", "Cyprus"),
    "CZ": ("Чешка", "Czechia"),
    "DK": ("Данска", "Denmark"),
    "EE": ("Естонија", "Estonia"),
    "FI": ("Финска", "Finland"),
    "FR": ("Франција", "France"),
    "DE": ("Германија", "Germany"),
    "GR": ("Грција", "Greece"),
    "HU": ("Унгарија", "Hungary"),
    "IE": ("Ирска", "Ireland"),
    "IT": ("Италија", "Italy"),
    "LV": ("Латвија", "Latvia"),
    "LT": ("Литванија", "Lithuania"),
    "LU": ("Луксембург", "Luxembourg"),
    "MT": ("Малта", "Malta"),
    "NL": ("Холандија", "Netherlands"),
    "PL": ("Полска", "Poland"),
    "PT": ("Португалија", "Portugal"),
    "RO": ("Романија", "Romania"),
    "SK": ("Словачка", "Slovakia"),
    "SI": ("Словенија", "Slovenia"),
    "ES": ("Шпанија", "Spain"),
    "SE": ("Шведска", "Sweden"),
    "IS": ("Исланд", "Iceland"),
    "LI": ("Лихтенштајн", "Liechtenstein"),
    "NO": ("Норвешка", "Norway"),
    "TR": ("Турција", "Turkey"),
    "CH": ("Швајцарија", "Switzerland"),
    "GB": ("Обединето Кралство", "United Kingdom"),
    "US": ("САД", "United States"),
    "AE": ("Обединети Арапски Емирати", "United Arab Emirates"),
}

TRAPS_MK = {
    "TR": "Турција **не е** членка на ЕУ ниту на ЕЕА и **не е** дел од Регионалниот договор за Западен Балкан. Ова е најчестата грешка кај патниците: географската близина и делумната припадност на Европа не значат европски роаминг режим.",
    "CH": "Швајцарија **не е** членка на ЕУ и **не е** дел од ЕЕА, иако е опкружена со земји од ЕУ. Роамингот се наплаќа по Зона 3.",
    "GB": "Обединетото Кралство се повлече од Европската унија и повеќе не е дел од ЕЕА. Од таа промена важат цените од Зона 3.",
    "IS": "Исланд не е членка на ЕУ, но **е** дел од Европскиот економски простор, па важат цените од Зона 2.",
    "NO": "Норвешка не е членка на ЕУ, но **е** дел од Европскиот економски простор, па важат цените од Зона 2.",
    "LI": "Лихтенштајн не е членка на ЕУ, но **е** дел од Европскиот економски простор, па важат цените од Зона 2.",
    "XK": "Косово е дел од Регионалниот договор за роаминг за Западен Балкан, па важи режимот без доплата.",
    "RS": "Србија е дел од Регионалниот договор за Западен Балкан. Роамингот е без доплата, за разлика од соседна Бугарија или Унгарија кои се во ЕУ и спаѓаат во Зона 2.",
    "GR": "Грција е членка на ЕУ, што значи Зона 2 и наплата по ограничени цени. Иако е соседна земја, режимот е поинаков од оној во Србија или Албанија.",
    "BG": "Бугарија е членка на ЕУ. И покрај тоа што е соседна земја, се применува Зона 2, а не режимот за Западен Балкан.",
}
TRAPS_EN = {
    "TR": "Turkey is **not** an EU or EEA member and is **not** party to the Western Balkans Regional Roaming Agreement. This is the most common traveller error: geographic proximity to Europe does not imply the European roaming regime.",
    "CH": "Switzerland is **not** an EU member and is **not** in the EEA, despite being surrounded by EU countries. Zone 3 rates apply.",
    "GB": "The United Kingdom withdrew from the European Union and is no longer in the EEA. Zone 3 rates have applied since that change.",
    "IS": "Iceland is not an EU member but **is** in the European Economic Area, so Zone 2 rates apply.",
    "NO": "Norway is not an EU member but **is** in the European Economic Area, so Zone 2 rates apply.",
    "LI": "Liechtenstein is not an EU member but **is** in the European Economic Area, so Zone 2 rates apply.",
    "RS": "Serbia is party to the Western Balkans Regional Roaming Agreement, so no surcharge applies, unlike neighbouring Bulgaria or Hungary which are EU members in Zone 2.",
    "GR": "Greece is an EU member, meaning Zone 2 and capped charging. Although it is a neighbouring country, the regime differs from Serbia or Albania.",
    "BG": "Bulgaria is an EU member. Despite being a neighbouring country, Zone 2 applies rather than the Western Balkans regime.",
}


def gen_country_sheets() -> None:
    y = C.CURRENT_YEAR
    zmap = {z.key: z for z in C.ZONES}
    for iso, zkey in C.COUNTRY_ZONES.items():
        if iso not in COUNTRY_NAMES or iso == "MK":
            continue
        mk_name, en_name = COUNTRY_NAMES[iso]
        z = zmap[zkey]
        packs = [p for p in C.ROAMING_PACKS if p["zone"] == zkey]
        free = zkey == "wb6_rlah"

        pack_mk = (
            "\n".join(
                f"| {p['code']} | {p['gb']} GB | {p['days']} дена | {money(p['price'][y])} {DEN} |"
                for p in packs
            )
            if packs
            else "| — | — | — | не е потребен пакет |"
        )
        pack_en = (
            "\n".join(
                f"| {p['code']} | {p['gb']} GB | {p['days']} days | {money(p['price'][y])} MKD |"
                for p in packs
            )
            if packs
            else "| — | — | — | no pack needed |"
        )

        note_mk = f"\n## Важна напомена\n\n{TRAPS_MK[iso]}\n" if iso in TRAPS_MK else ""
        note_en = f"\n## Important note\n\n{TRAPS_EN[iso]}\n" if iso in TRAPS_EN else ""

        adv_mk = (
            "Не ви треба никаква подготовка. Домашната квота важи автоматски."
            if free
            else f"Активирајте роаминг пакет пред патувањето. Без пакет, {money(z.mb[y])} {DEN} по MB "
            f"значи дека 1 GB чини околу {money(z.mb[y]*1024)} {DEN}."
        )
        adv_en = (
            "No preparation needed. Your domestic allowance applies automatically."
            if free
            else f"Activate a roaming pack before travelling. Without one, {money(z.mb[y])} MKD per MB "
            f"means 1 GB costs roughly {money(z.mb[y]*1024)} MKD."
        )

        w(
            f"countries/op-country-{iso.lower()}-mk.md",
            front(f"op-country-{iso.lower()}", f"Роаминг во {mk_name}", "mk", y, "country")
            + f"""# Роаминг во {mk_name}

**Земја:** {mk_name} ({iso})
**Зона:** {z.idx} — {z.name_mk}
**Режим:** {z.regime_mk}
**Правна основа:** {z.basis_mk}

## Цени

| Услуга | Цена |
|---|---|
| Интернет по MB | {money(z.mb[y])} {DEN} |
| Интернет по GB (пресметковно) | {money(z.mb[y]*1024)} {DEN} |
| Појдовна минута | {money(z.out_min[y])} {DEN} |
| Дојдовна минута | {money(z.in_min[y])} {DEN} |
| SMS | {money(z.sms[y])} {DEN} |

## Достапни роаминг пакети

| Код | Количина | Важност | Цена |
|---|---|---|---|
{pack_mk}

## Совет пред патување

{adv_mk}

Месечниот лимит од {money(C.FUP['roaming_monthly_cap_mkd'])} {DEN} важи и за оваа дестинација.
Итните повици кон 112 се секогаш бесплатни.
{note_mk}
## Проверка на состојба во странство

`*123#` ја прикажува преостанатата квота и активните пакети. Мој Вардар работи и преку
роаминг без наплата на податоци.
""",
        )

        w(
            f"countries/op-country-{iso.lower()}-en.md",
            front(f"op-country-{iso.lower()}", f"Roaming in {en_name}", "en", y, "country")
            + f"""# Roaming in {en_name}

**Country:** {en_name} ({iso})
**Zone:** {z.idx} — {z.name_en}
**Regime:** {z.regime_en}
**Legal basis:** {z.basis_en}

## Rates

| Service | Price |
|---|---|
| Data per MB | {money(z.mb[y])} MKD |
| Data per GB (derived) | {money(z.mb[y]*1024)} MKD |
| Outgoing minute | {money(z.out_min[y])} MKD |
| Incoming minute | {money(z.in_min[y])} MKD |
| SMS | {money(z.sms[y])} MKD |

## Available roaming packs

| Code | Volume | Validity | Price |
|---|---|---|---|
{pack_en}

## Before you travel

{adv_en}

The monthly cap of {money(C.FUP['roaming_monthly_cap_mkd'])} MKD applies to this destination.
Emergency calls to 112 are always free.
{note_en}
""",
        )


MONTHS_MK = [
    "јануари",
    "февруари",
    "март",
    "април",
    "мај",
    "јуни",
    "јули",
    "август",
    "септември",
    "октомври",
    "ноември",
    "декември",
]
MONTHS_EN = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
CITIES = [
    ("Скопје", "Skopje"),
    ("Битола", "Bitola"),
    ("Куманово", "Kumanovo"),
    ("Прилеп", "Prilep"),
    ("Тетово", "Tetovo"),
    ("Охрид", "Ohrid"),
    ("Велес", "Veles"),
    ("Штип", "Stip"),
    ("Струмица", "Strumica"),
    ("Гостивар", "Gostivar"),
    ("Кавадарци", "Kavadarci"),
    ("Кочани", "Kocani"),
]


def gen_bulletins() -> None:
    """Monthly network bulletins. Volume plus a genuine recency-filtering test:
    a question about current coverage must not retrieve a 2024 bulletin."""
    for yi, y in enumerate((2025, 2026)):
        for m in range(12):
            if y == 2026 and m > 6:
                continue
            city_mk, city_en = CITIES[(m + yi * 5) % len(CITIES)]
            city2_mk, city2_en = CITIES[(m + yi * 5 + 4) % len(CITIES)]
            sites = 8 + (m * 3 + yi * 7) % 22
            pct = 62 + (m * 2 + yi * 9) % 33
            w(
                f"bulletins/op-bulletin-{y}-{m+1:02d}-mk.md",
                front(
                    f"op-bulletin-{y}-{m+1:02d}",
                    f"Билтен за мрежата — {MONTHS_MK[m]} {y}",
                    "mk",
                    y,
                    "bulletin",
                )
                + f"""# Билтен за мрежата — {MONTHS_MK[m]} {y}

## Проширување на покриеноста

Во текот на {MONTHS_MK[m]} {y} пуштени се во работа **{sites} нови базни станици**, со
тежиште на {city_mk} и околината. Покриеноста со 5G во {city_mk} достигна **{pct}%**
од населението.

Работите во {city2_mk} продолжуваат и се очекува завршување во следниот квартал.

## Планирани работи

Планираните работи на мрежата кои може да предизвикаат прекин подолг од 30 минути се
објавуваат најмалку 24 часа однапред преку SMS и на статусната страница. Во овој месец
беа изведени {2 + m % 4} такви интервенции, сите во периодот меѓу 02:00 и 05:00 часот.

## Квалитет на услугата

| Показател | Вредност |
|---|---|
| Достапност на мрежата | {99.1 + (m % 8) / 10:.1f}% |
| Просечна брзина на преземање, 4G | {28 + m * 2} Mbps |
| Просечна брзина на преземање, 5G | {180 + m * 7} Mbps |
| Успешност на воспоставени повици | {98.2 + (m % 6) / 10:.1f}% |

## Забелешка

Наведените вредности се просеци за целата мрежа и не претставуваат гарантирана брзина
на поединечна локација. Реалната брзина зависи од оддалеченоста од базната станица,
оптовареноста на ќелијата и способностите на уредот.
""",
            )
            w(
                f"bulletins/op-bulletin-{y}-{m+1:02d}-en.md",
                front(
                    f"op-bulletin-{y}-{m+1:02d}",
                    f"Network bulletin — {MONTHS_EN[m]} {y}",
                    "en",
                    y,
                    "bulletin",
                )
                + f"""# Network bulletin — {MONTHS_EN[m]} {y}

## Coverage expansion

During {MONTHS_EN[m]} {y}, **{sites} new base stations** entered service, concentrated
around {city_en}. 5G population coverage in {city_en} reached **{pct}%**.

Work in {city2_en} continues, with completion expected next quarter.

## Service quality

| Indicator | Value |
|---|---|
| Network availability | {99.1 + (m % 8) / 10:.1f}% |
| Average 4G download | {28 + m * 2} Mbps |
| Average 5G download | {180 + m * 7} Mbps |
| Call setup success rate | {98.2 + (m % 6) / 10:.1f}% |

These are network-wide averages and do not represent a guaranteed speed at any single
location.
""",
            )


# ═══════════════════════════════════ knowledge base articles + coverage pages
def gen_kb_articles() -> None:
    """One article per error code x device family. Highly specific, easily
    confused with each other, which is exactly the discrimination test."""
    y = C.CURRENT_YEAR
    for code, mk_t, en_t, mk_c, en_c in C.ERROR_CODES:
        for dev in C.DEVICES:
            slug = f"{code.lower()}-{dev['model'].lower().replace(' ', '-')}"
            w(
                f"kb/op-kb-{slug}-mk.md",
                front(f"op-kb-{slug}", f"{code} на {dev['model']}", "mk", y, "kb")
                + f"""# {code}: {mk_t}
## Уред: {dev['model']}

**Причина:** {mk_c}

## Решение

1. Рестартирајте го уредот и обидете се повторно.
2. Проверете дали картичката е правилно вметната и без оштетување.
3. За {dev['model']}: отворете Поставки, Мобилна мрежа, и проверете дали е избран
   автоматски избор на оператор.
4. Ако грешката се повторува, ресетирајте ги мрежните поставки. Ова ги брише
   зачуваните Wi-Fi лозинки но не влијае на податоците.
5. Тестирајте ја картичката во друг уред за да утврдите дали проблемот е во
   картичката или во {dev['model']}.

## Кога да се јавите на поддршка

Ако грешката {code} се повторува по сите чекори, јавете се на 1300 и наведете го
кодот, моделот {dev['model']}, и точното време на последната појава. Поддршката
може да провери дали има проблем на страна на мрежата за вашата картичка.
""",
            )
            w(
                f"kb/op-kb-{slug}-en.md",
                front(f"op-kb-{slug}", f"{code} on {dev['model']}", "en", y, "kb")
                + f"""# {code}: {en_t}
## Device: {dev['model']}

**Cause:** {en_c}

## Resolution

1. Restart the device and retry.
2. Check the SIM is seated correctly and undamaged.
3. On {dev['model']}: open Settings, Mobile network, and confirm automatic
   operator selection is enabled.
4. If the error repeats, reset network settings. This clears saved Wi-Fi
   passwords but does not affect your data.
5. Test the SIM in another device to determine whether the fault is with the
   SIM or with the {dev['model']}.

## When to contact support

If error {code} persists after all steps, call 1300 quoting the code, the model
{dev['model']}, and the exact time of the last occurrence.
""",
            )


def gen_coverage() -> None:
    y = C.CURRENT_YEAR
    for i, (mk_city, en_city, pop) in enumerate(C.CITIES_FULL):
        c4 = 96 + (i % 4)
        c5 = max(0, 88 - i * 3)
        sites = 4 + (pop // 9000)
        w(
            f"coverage/op-coverage-{en_city.lower().replace(' ', '-')}-mk.md",
            front(
                f"op-coverage-{en_city.lower().replace(' ','-')}",
                f"Покриеност — {mk_city}",
                "mk",
                y,
                "coverage",
            )
            + f"""# Покриеност во {mk_city}

| Показател | Вредност |
|---|---|
| Население | {pop:,} |
| Покриеност 4G | {c4}% |
| Покриеност 5G | {c5}% |
| Базни станици | {sites} |
| Просечна брзина 4G | {32 + i % 18} Mbps |
| Просечна брзина 5G | {"—" if c5 == 0 else f"{150 + i * 6} Mbps"} |

## Забелешки за подрачјето

{"5G сè уште не е достапно во ова подрачје. Планирано е воведување во наредните квартали." if c5 == 0 else f"5G е достапно во централните делови на {mk_city}."}

Покриеноста во внатрешност зависи од градбата. Ѕидови од армиран бетон и прозорци со
метализирана фолија значително го намалуваат сигналот. За подобрување препорачуваме
активирање на Wi-Fi Calling.

## Планирани работи

Проширувањето на мрежата во {mk_city} продолжува. Информации за планирани прекини се
објавуваат најмалку 24 часа однапред преку SMS и на статусната страница.

Наведените вредности се просеци за подрачјето и не претставуваат гарантирана брзина
на поединечна локација.
""",
        )
        w(
            f"coverage/op-coverage-{en_city.lower().replace(' ', '-')}-en.md",
            front(
                f"op-coverage-{en_city.lower().replace(' ','-')}",
                f"Coverage — {en_city}",
                "en",
                y,
                "coverage",
            )
            + f"""# Coverage in {en_city}

| Indicator | Value |
|---|---|
| Population | {pop:,} |
| 4G coverage | {c4}% |
| 5G coverage | {c5}% |
| Base stations | {sites} |
| Average 4G speed | {32 + i % 18} Mbps |
| Average 5G speed | {"—" if c5 == 0 else f"{150 + i * 6} Mbps"} |

{"5G is not yet available in this area. Rollout is planned for coming quarters." if c5 == 0 else f"5G is available in central {en_city}."}

Indoor coverage depends on construction. Reinforced concrete and metallised window
coatings reduce signal materially. Wi-Fi Calling is recommended where indoor
coverage is weak.

Figures are area averages and do not represent a guaranteed speed at any single location.
""",
        )


# ═══════════════════════════ Вардар Поени: programme terms + device catalogue
def gen_points_programme() -> None:
    y, P = C.CURRENT_YEAR, C.POINTS
    tiers_mk = "\n".join(
        f"| {mk} | {th:,} поени | ×{mult} | {note} |".replace(",", ".")
        for mk, en, th, mult, note in P["tiers"]
    )
    tiers_en = "\n".join(
        f"| {en} | {th:,} points | ×{mult} | reached after {th:,} points in 12 months |"
        for mk, en, th, mult, note in P["tiers"]
    )

    w(
        f"points/op-points-terms-{y}-mk.md",
        front(f"op-points-terms-{y}", "Вардар Поени — општи услови", "mk", y, "points")
        + f"""# Вардар Поени
## Општи услови на програмата за лојалност

## 1. Учество
Програмата е достапна за сите претплатници со активен претплатнички договор.
Пред-платените корисници не учествуваат. Пријавувањето е автоматско при активација.

## 2. Собирање поени
За секои потрошени **{P['earn_per_mkd']} денари** на месечната сметка се доделува **1 поен**.
Се земаат предвид: месечната претплата, дополнителните пакети, роаминг пакетите и
ратите за уред. Не се земаат предвид: услуги со додадена вредност, ДДВ на трети лица,
и износи по рекламација што се сторнирани.

Поените се доделуваат по **плаќање** на сметката, не по нејзиното издавање.

## 3. Бонуси
- **Автоматско плаќање:** +{P['autopay_bonus_pct']}% поени секој месец
- **Верност:** +{P['tenure_bonus_per_year']}% за секоја полна година непрекинат договор, најмногу до +{P['tenure_cap_pct']}%
- Бонусите се кумулативни и се пресметуваат на основниот износ

## 4. Нивоа

| Ниво | Праг | Множител | Услов |
|---|---|---|---|
{tiers_mk}

Нивото се пресметува од поените собрани во последните 12 месеци и се ревидира секој
месец. Симнување на пониско ниво се применува со едномесечно одложување.

## 5. Важност
Поените важат **{P['expiry_months']} месеци** од денот на доделување. Истекуваат по принципот
прв влезен, прв излезен. Известување се испраќа 60 и 14 дена пред истек.

## 6. Искористување
Минимум за искористување е **{P['min_redeem']} поени**. Поените може да се искористат за:
уред од каталогот, додатоци, дополнителни пакети за интернет, или кредит на сметка
по курс од 100 поени за 50 денари.

Комбинирано плаќање поени плус готовина е дозволено за уреди.

## 7. Ограничувања
Поените не се пренесуваат на друго лице, не се заменуваат за готовина, и се губат
при раскинување на договорот. При пренос на бројот кај друг оператор поените се губат
во моментот на успешен пренос.

При предвремено раскинување во рок од 6 месеци по искористување на поени за уред,
операторот има право да ја наплати разликата до редовната цена на уредот.
""",
    )
    w(
        f"points/op-points-terms-{y}-en.md",
        front(f"op-points-terms-{y}", "Vardar Points — programme terms", "en", y, "points")
        + f"""# Vardar Points
## Loyalty programme terms

## Earning
**1 point per {P['earn_per_mkd']} MKD** paid. Counted: monthly fee, add-ons, roaming packs,
device instalments. Not counted: premium services and amounts reversed after a complaint.
Points are credited on **payment**, not on invoicing.

## Bonuses
Autopay +{P['autopay_bonus_pct']}%. Tenure +{P['tenure_bonus_per_year']}% per full year, capped at +{P['tenure_cap_pct']}%. Cumulative.

## Tiers

| Tier | Threshold | Multiplier | Condition |
|---|---|---|---|
{tiers_en}

Tier is computed from points earned in the last 12 months and reviewed monthly.
Downgrades apply with one month's delay.

## Validity
Points expire **{P['expiry_months']} months** after award, first in first out. Notice at 60 and 14 days.

## Redemption
Minimum **{P['min_redeem']} points**. Redeemable against devices, accessories, data add-ons,
or bill credit at 100 points per 50 MKD. Points plus cash is permitted for devices.

## Restrictions
Non-transferable, no cash value, forfeited on contract termination and on successful
number portability. Early termination within 6 months of redeeming points against a
device entitles the operator to charge the difference to full retail price.
""",
    )

    rows_mk, rows_en = [], []
    for b, m, tier, mkd, pts, *_ in C.DEVICE_CATALOG:
        half = pts // 2
        rows_mk.append(
            f"| {b} {m} | {mkd:,} ден. | {pts:,} | {half:,} + {mkd//2:,} ден. |".replace(",", ".")
        )
        rows_en.append(f"| {b} {m} | {mkd:,} MKD | {pts:,} | {half:,} + {mkd//2:,} MKD |")
    acc_mk = "\n".join(
        f"| {mk} | {mkd:,} ден. | {pts:,} |".replace(",", ".") for mk, en, mkd, pts in C.ACCESSORIES
    )
    acc_en = "\n".join(f"| {en} | {mkd:,} MKD | {pts:,} |" for mk, en, mkd, pts in C.ACCESSORIES)

    w(
        f"points/op-points-catalog-{y}-mk.md",
        front(f"op-points-catalog-{y}", "Каталог за искористување поени", "mk", y, "points")
        + f"""# Каталог за искористување на Вардар Поени

Цените во поени се менуваат квартално. Каталогот важи од 1 јануари {y}.

## Уреди

| Уред | Редовна цена | Целосно со поени | Комбинирано |
|---|---|---|---|
"""
        + "\n".join(rows_mk)
        + f"""

Комбинираното плаќање значи половина од поените плус половина од цената во денари.
Достапноста зависи од залиха. Резервацијата трае 7 дена.

## Додатоци

| Додаток | Редовна цена | Поени |
|---|---|---|
{acc_mk}

## Пакети за интернет и кредит

| Награда | Поени |
|---|---|
| Додаток 1 GB | 1.500 |
| Додаток 5 GB | 4.000 |
| Додаток 20 GB | 9.000 |
| Роаминг ЕУ 1 GB | 3.000 |
| Кредит на сметка 500 ден. | 1.000 |
| Кредит на сметка 1.000 ден. | 2.000 |
""",
    )
    w(
        f"points/op-points-catalog-{y}-en.md",
        front(f"op-points-catalog-{y}", "Points redemption catalogue", "en", y, "points")
        + f"""# Vardar Points redemption catalogue

Point prices are revised quarterly. Effective 1 January {y}.

## Devices

| Device | Retail | Full points | Points + cash |
|---|---|---|---|
"""
        + "\n".join(rows_en)
        + f"""

## Accessories

| Accessory | Retail | Points |
|---|---|---|
{acc_en}

## Data and credit

| Reward | Points |
|---|---|
| 1 GB add-on | 1,500 |
| 5 GB add-on | 4,000 |
| 20 GB add-on | 9,000 |
| EU roaming 1 GB | 3,000 |
| 500 MKD bill credit | 1,000 |
| 1,000 MKD bill credit | 2,000 |
""",
    )


def gen_device_specs() -> None:
    y = C.CURRENT_YEAR
    for (
        b,
        m,
        tier,
        mkd,
        pts,
        disp,
        chip,
        ram,
        sto,
        cam,
        batt,
        esim,
        ip,
        wt,
        bands,
    ) in C.DEVICE_CATALOG:
        slug = f"{b}-{m}".lower().replace(" ", "-").replace("+", "plus")
        inst24 = round(mkd / 24)
        supported = bands != "—"
        w(
            f"catalog/op-katalog-{slug}-mk.md",
            front(f"op-katalog-{slug}", f"Спецификација — {b} {m}", "mk", y, "device-spec")
            + f"""# {b} {m}

| Спецификација | Вредност |
|---|---|
| Екран | {disp} |
| Процесор | {chip} |
| Меморија | {ram} GB RAM |
| Простор | {sto} GB |
| Главна камера | {cam} MP |
| Батерија | {batt} mAh |
| eSIM | {"поддржано" if esim else "не е поддржано"} |
| Отпорност | {ip} |
| Тежина | {wt} g |
| 5G опсези | {bands} |

## Цена и начини на набавка

| Начин | Износ |
|---|---|
| Редовна цена | {mkd:,} ден. |
| На рати, 24 месеци | {inst24:,} ден. месечно, 0% камата |
| Целосно со Вардар Поени | {pts:,} поени |
| Комбинирано | {pts//2:,} поени + {mkd//2:,} ден. |

## Компатибилност со мрежата

{"Уредот поддржува 5G на опсезите " + bands + ", што ги вклучува опсезите на нашата мрежа (n1, n3, n78). Поддржан е и VoLTE." if supported else "Уредот не поддржува 5G. Работи на 4G мрежата со поддршка за VoLTE."}

{"eSIM е поддржано. Профилот може да се активира преку QR код без физичка картичка." if esim else "eSIM не е поддржано на овој модел. Потребна е физичка SIM картичка."}

## Забелешка
Спецификациите се дадени од производителот и се подложни на промена. Наведените цени
во денари и во поени се синтетички и служат за демонстрација.
""".replace(",", "."),
        )
        w(
            f"catalog/op-katalog-{slug}-en.md",
            front(f"op-katalog-{slug}", f"Specification — {b} {m}", "en", y, "device-spec")
            + f"""# {b} {m}

| Specification | Value |
|---|---|
| Display | {disp} |
| Chipset | {chip} |
| Memory | {ram} GB RAM |
| Storage | {sto} GB |
| Main camera | {cam} MP |
| Battery | {batt} mAh |
| eSIM | {"supported" if esim else "not supported"} |
| Ingress protection | {ip} |
| Weight | {wt} g |
| 5G bands | {bands} |

## Price and acquisition

| Method | Amount |
|---|---|
| Retail | {mkd:,} MKD |
| 24-month instalments | {inst24:,} MKD/month, 0% interest |
| Full Vardar Points | {pts:,} points |
| Points plus cash | {pts//2:,} points + {mkd//2:,} MKD |

## Network compatibility

{"This device supports 5G on bands " + bands + ", which covers our network bands n1, n3 and n78. VoLTE is supported." if supported else "This device does not support 5G. It operates on 4G with VoLTE support."}

{"eSIM is supported, so the profile can be activated by QR code without a physical SIM." if esim else "eSIM is not supported on this model. A physical SIM is required."}
""",
        )


# ══════════════════════════════ full device spec sheets (75 devices, 2 langs)
KIND_MK = {
    "phone": "Мобилен телефон",
    "tablet": "Таблет",
    "watch": "Паметен часовник",
    "router": "Рутер",
}
KIND_EN = {"phone": "Mobile phone", "tablet": "Tablet", "watch": "Smartwatch", "router": "Router"}


def _pts(mkd: int) -> int:
    return round(mkd * 1.92 / 500) * 500


def gen_full_specs() -> None:
    y = C.CURRENT_YEAR
    for d in C.DEVICES_FULL:
        slug = f"{d['brand']}-{d['model']}".lower().replace(" ", "-").replace("+", "plus")
        pts = _pts(d["mkd"])
        months = 36 if d["mkd"] > 70000 else 24 if d["mkd"] > 15000 else 12
        inst = round(d["mkd"] / months)
        has5g = d["bands5g"] != "—"
        cams = [
            ("Главна", "Main", d["cam_main"]),
            ("Ултра-широка", "Ultra-wide", d["cam_ultra"]),
            ("Телефото", "Telephoto", d["cam_tele"]),
            ("Предна", "Front", d["cam_front"]),
        ]
        cam_mk = "\n".join(f"| {a} | {v} MP |" for a, b, v in cams if v)
        cam_en = "\n".join(f"| {b} | {v} MP |" for a, b, v in cams if v)

        disp_mk = (
            (
                f"| Екран | {d['disp_in']}\" {d['panel']} |\n| Освежување | {d['hz']} Hz |\n"
                f"| Резолуција | {d['res']} |\n"
            )
            if d["disp_in"]
            else ""
        )
        disp_en = (
            (
                f"| Display | {d['disp_in']}\" {d['panel']} |\n| Refresh rate | {d['hz']} Hz |\n"
                f"| Resolution | {d['res']} |\n"
            )
            if d["disp_in"]
            else ""
        )
        batt_mk = (
            (
                f"| Батерија | {d['batt']} mAh |\n| Полнење | {d['charge_w']} W |\n"
                + (f"| Безжично полнење | {d['wireless_w']} W |\n" if d["wireless_w"] else "")
            )
            if d["batt"]
            else ""
        )
        batt_en = (
            (
                f"| Battery | {d['batt']} mAh |\n| Wired charging | {d['charge_w']} W |\n"
                + (f"| Wireless charging | {d['wireless_w']} W |\n" if d["wireless_w"] else "")
            )
            if d["batt"]
            else ""
        )

        w(
            f"specs/op-spec-{slug}-mk.md",
            front(
                f"op-spec-{slug}",
                f"Спецификација — {d['brand']} {d['model']}",
                "mk",
                y,
                "device-spec",
            )
            + f"""# {d['brand']} {d['model']}

**Категорија:** {KIND_MK[d['kind']]} · **Година:** {d['year']}

## Технички спецификации

| Спецификација | Вредност |
|---|---|
{disp_mk}| Процесор | {d['chip']} |
| RAM меморија | {d['ram']} GB |
"""
            + (f"| Внатрешна меморија | {d['storage']} GB |\n" if d["storage"] else "")
            + batt_mk
            + f"""| Отпорност | {d['ip']} |
| Тежина | {d['weight']} g |
| Оперативен систем | {d['os']} |

"""
            + (f"## Камери\n\n| Камера | Резолуција |\n|---|---|\n{cam_mk}\n\n" if cam_mk else "")
            + f"""## Мрежна поддршка

| Ставка | Вредност |
|---|---|
| 5G | {"поддржано" if has5g else "не е поддржано"} |
| 5G опсези | {d['bands5g']} |
| eSIM | {"поддржано" if d['esim'] else "не е поддржано"} |
| VoLTE | поддржано |
| Wi-Fi Calling | поддржано |

{"Уредот ги поддржува опсезите на нашата 5G мрежа (n1, n3, n78)." if has5g and any(b in d['bands5g'] for b in ("n1","n3","n78")) else "Уредот работи на 4G мрежата."}
{"eSIM профилот се активира со QR код без физичка картичка." if d['esim'] else "Потребна е физичка SIM картичка."}

## Начини на набавка

| Начин | Износ |
|---|---|
| Редовна цена | {d['mkd']:,} ден. |
| На рати, {months} месеци | {inst:,} ден. месечно, 0% камата |
| Целосно со Вардар Поени | {pts:,} поени |
| Комбинирано | {pts//2:,} поени + {d['mkd']//2:,} ден. |

## Забелешка
Спецификациите се дадени од производителот и подложни на промена. Цените во денари и
во поени се синтетички и служат за демонстрација на системот.
""".replace(",", "."),
        )

        w(
            f"specs/op-spec-{slug}-en.md",
            front(
                f"op-spec-{slug}",
                f"Specification — {d['brand']} {d['model']}",
                "en",
                y,
                "device-spec",
            )
            + f"""# {d['brand']} {d['model']}

**Category:** {KIND_EN[d['kind']]} · **Year:** {d['year']}

## Technical specifications

| Specification | Value |
|---|---|
{disp_en}| Chipset | {d['chip']} |
| RAM | {d['ram']} GB |
"""
            + (f"| Storage | {d['storage']} GB |\n" if d["storage"] else "")
            + batt_en
            + f"""| Ingress protection | {d['ip']} |
| Weight | {d['weight']} g |
| Operating system | {d['os']} |

"""
            + (f"## Cameras\n\n| Camera | Resolution |\n|---|---|\n{cam_en}\n\n" if cam_en else "")
            + f"""## Network support

| Item | Value |
|---|---|
| 5G | {"supported" if has5g else "not supported"} |
| 5G bands | {d['bands5g']} |
| eSIM | {"supported" if d['esim'] else "not supported"} |
| VoLTE | supported |
| Wi-Fi Calling | supported |

## Acquisition

| Method | Amount |
|---|---|
| Retail | {d['mkd']:,} MKD |
| {months}-month instalments | {inst:,} MKD/month, 0% interest |
| Full Vardar Points | {pts:,} points |
| Points plus cash | {pts//2:,} points + {d['mkd']//2:,} MKD |
""",
        )

    # comparison sheets, one per category: forces numeric discrimination
    for kind in ("phone", "tablet", "watch", "router"):
        ds = [d for d in C.DEVICES_FULL if d["kind"] == kind]
        rows_mk = "\n".join(
            f"| {d['brand']} {d['model']} | {d['mkd']:,} ден. | {_pts(d['mkd']):,} | "
            f"{d['ram']} GB | {d['storage'] or '—'} GB | {d['batt'] or '—'} mAh | "
            f"{'да' if d['esim'] else 'не'} | {'да' if d['bands5g'] != '—' else 'не'} |".replace(
                ",", "."
            )
            for d in sorted(ds, key=lambda x: -x["mkd"])
        )
        w(
            f"specs/op-compare-{kind}-mk.md",
            front(f"op-compare-{kind}", f"Споредба — {KIND_MK[kind]}", "mk", y, "device-compare")
            + f"""# Споредба на сите модели: {KIND_MK[kind]}

| Модел | Цена | Поени | RAM | Меморија | Батерија | eSIM | 5G |
|---|---|---|---|---|---|---|---|
{rows_mk}

Сортирано по цена, опаѓачки. Достапноста зависи од залиха.
""",
        )

        rows_en = "\n".join(
            f"| {d['brand']} {d['model']} | {d['mkd']:,} MKD | {_pts(d['mkd']):,} | "
            f"{d['ram']} GB | {d['storage'] or '—'} GB | {d['batt'] or '—'} mAh | "
            f"{'yes' if d['esim'] else 'no'} | {'yes' if d['bands5g'] != '—' else 'no'} |"
            for d in sorted(ds, key=lambda x: -x["mkd"])
        )
        w(
            f"specs/op-compare-{kind}-en.md",
            front(f"op-compare-{kind}", f"Comparison — {kind}", "en", y, "device-compare")
            + f"""# All models compared: {kind}

| Model | Price | Points | RAM | Storage | Battery | eSIM | 5G |
|---|---|---|---|---|---|---|---|
{rows_en}

Sorted by price, descending. Availability depends on stock.
""",
        )



# ─────────────────────────────────────────────────────────────────── prepaid
def gen_prepaid() -> None:
    """Prepaid tariffs.

    The corpus was 100% postpaid, which made a whole class of question
    unanswerable and, worse, made it *confidently* answerable with the postpaid
    number. Prepaid gives several questions two correct answers that differ,
    so retrieval has to discriminate on subscription type rather than topic.
    """
    for pp in C.PREPAID:
        for y in C.YEARS:
            gb = pp.data_gb[y]
            prev = (
                f"\nВо {y-1} година пакетот содржеше {pp.data_gb[y-1]} GB.\n"
                if y > C.YEARS[0]
                else "\n"
            )
            r = C.PREPAID_RULES
            w(
                f"prepaid/op-pripejd-{pp.code.lower()}-{y}-mk.md",
                front(
                    f"op-pripejd-{pp.code.lower()}-{y}",
                    f"Припејд пакет — {pp.name} ({y})",
                    "mk",
                    y,
                    "prepaid",
                )
                + f"""# {pp.name}
## Припејд пакет за {y} година

Ова е **припејд** пакет. Не се склучува договор, нема минимален период и нема
надоместок за предвремено раскинување.

| Ставка | Вредност |
|---|---|
| Потребна дополна | **{money(pp.topup)} {DEN}** |
| Важност на пакетот | {pp.days} дена |
| Интернет | {gb} GB |
| Разговори | {pp.minutes} |
| SMS | {pp.sms} |
{prev}
## По потрошена квота

Наплатата продолжува од расположливиот кредит по стандардна тарифа:
{money(r['out_of_bundle_per_mb'])} {DEN} по MB, {money(r['out_of_bundle_per_min'])} {DEN}
по минута, {money(r['out_of_bundle_per_sms'])} {DEN} по SMS. Кога кредитот ќе се
потроши, услугата запира. Нема фактура и нема пречекорување.

## Важност на кредитот

Неискористениот кредит важи {r['credit_validity_days']} дена од последната дополна.
По истекот следуваат {r['grace_days']} дена во кои бројот прима повици но не може да
троши. По вкупно {r['number_release_days']} дена без дополна бројот се враќа во
слободниот опсег и не може да се поврати.

## Разлика во однос на постпејд

| | Припејд | Постпејд |
|---|---|---|
| Договор | нема | {C.CONTRACT_BY_YEAR[y]['min_term_months']} месеци |
| Предвремено раскинување | без надоместок | {C.CONTRACT_BY_YEAR[y]['early_fee_pct']}% од преостанатите месеци |
| Право на откажување во 14 дена | не се применува | се применува |
| Фактура | нема | месечна |
| Роаминг | бара позитивен кредит од најмалку {money(r['roaming_min_balance_mkd'])} {DEN} | вклучен во фактурата |
""",
            )

            w(
                f"prepaid/op-prepaid-{pp.code.lower()}-{y}-en.md",
                front(
                    f"op-pripejd-{pp.code.lower()}-{y}",
                    f"Prepaid bundle — {pp.name} ({y})",
                    "en",
                    y,
                    "prepaid",
                )
                + f"""# {pp.name}
## Prepaid bundle for {y}

This is a **prepaid** product. There is no contract, no minimum term and no
early termination fee.

| Item | Value |
|---|---|
| Top-up required | **{money(pp.topup)} MKD** |
| Bundle validity | {pp.days} days |
| Data | {gb} GB |
| Voice | {pp.minutes} |
| SMS | {pp.sms} |

## After the allowance is used

Charging continues from the remaining credit at the standard rate:
{money(r['out_of_bundle_per_mb'])} MKD per MB, {money(r['out_of_bundle_per_min'])} MKD
per minute, {money(r['out_of_bundle_per_sms'])} MKD per SMS. When the credit runs out
the service stops. There is no invoice and no overage.

## Credit validity

Unused credit is valid for {r['credit_validity_days']} days from the last top-up.
After that the number enters a {r['grace_days']}-day grace period during which it can
receive calls but not spend. After {r['number_release_days']} days without a top-up
the number returns to the free pool and cannot be recovered.

## Difference from postpaid

| | Prepaid | Postpaid |
|---|---|---|
| Contract | none | {C.CONTRACT_BY_YEAR[y]['min_term_months']} months |
| Early termination | no fee | {C.CONTRACT_BY_YEAR[y]['early_fee_pct']}% of remaining months |
| 14-day right of withdrawal | does not apply | applies |
| Invoice | none | monthly |
| Roaming | requires credit of at least {money(r['roaming_min_balance_mkd'])} MKD | billed |
""",
            )

    # ── prepaid roaming, where the fair use anchor differs from postpaid
    r = C.PREPAID_RULES
    for y in C.YEARS:
        rows_mk, rows_en = [], []
        for topup in (200, 350, 600, 1000, 2000):
            fup = min(topup / 100 * r["wb6_fup_gb_per_100_mkd"], r["wb6_fup_cap_gb"])
            rows_mk.append(f"| {money(topup)} {DEN} | {fup:.1f} GB |")
            rows_en.append(f"| {money(topup)} MKD | {fup:.1f} GB |")

        w(
            f"prepaid/op-pripejd-roaming-{y}-mk.md",
            front(f"op-pripejd-roaming-{y}", f"Припејд роаминг ({y})", "mk", y, "prepaid")
            + f"""# Припејд роаминг
## Правила за {y} година

Роамингот е достапен за припејд корисници со кредит од најмалку
{money(r['roaming_min_balance_mkd'])} {DEN}. Услугата се исклучува автоматски штом
кредитот падне под нула, без пречекорување.

## Западен Балкан — политика на правична употреба

За постпејд корисници квотата за правична употреба во Западен Балкан се врзува за
месечната претплата. **За припејд корисници таа се врзува за вкупната дополна во
последните 30 дена**, по {r['wb6_fup_gb_per_100_mkd']} GB на секои 100 {DEN},
најмногу {r['wb6_fup_cap_gb']} GB.

| Дополна во последните 30 дена | Квота во Западен Балкан |
|---|---|
""" + "\n".join(rows_mk) + f"""

Ова е честа причина за недоразбирање. Постпејд корисник со пакет M ја носи целата
домашна квота во Западен Балкан. Припејд корисник со иста потрошувачка добива
пресметка по горната табела, што вообичаено е помалку.

## ЕУ и останати земји

Во ЕУ важи ограничена наплата по MB од кредитот. Во останатите земји важи полна
меѓународна тарифа. Пакетите за роаминг може да се купат само додека кредитот е
позитивен.
""",
        )

        w(
            f"prepaid/op-prepaid-roaming-{y}-en.md",
            front(f"op-pripejd-roaming-{y}", f"Prepaid roaming ({y})", "en", y, "prepaid")
            + f"""# Prepaid roaming
## Rules for {y}

Roaming is available to prepaid customers holding at least
{money(r['roaming_min_balance_mkd'])} MKD of credit. The service stops automatically
when the credit reaches zero. There is no overage.

## Western Balkans fair use

For postpaid customers the Western Balkans fair use allowance is anchored to the
monthly fee. **For prepaid customers it is anchored to the total topped up in the
last 30 days**, at {r['wb6_fup_gb_per_100_mkd']} GB per 100 MKD, capped at
{r['wb6_fup_cap_gb']} GB.

| Topped up in the last 30 days | Western Balkans allowance |
|---|---|
""" + "\n".join(rows_en) + """

This is a common source of confusion. A postpaid customer on plan M carries the
full domestic allowance into the Western Balkans. A prepaid customer with the same
spend is assessed against the table above, which is usually less.

## EU and rest of world

In the EU, capped per-MB charging applies against the credit. Elsewhere the full
international tariff applies. Roaming packs can only be bought while the credit is
positive.
""",
        )

    # ── top-up channels and the prepaid-to-postpaid migration
    w(
        "prepaid/op-pripejd-dopolnuvanje-mk.md",
        front("op-pripejd-dopolnuvanje", "Дополнување на кредит", "mk", C.CURRENT_YEAR, "prepaid")
        + f"""# Дополнување на припејд кредит

Минимална дополна {money(r['min_topup_mkd'])} {DEN}. Максимално салдо
{money(r['max_balance_mkd'])} {DEN}; уплата над тоа се одбива.

| Канал | Провизија | Време до книжење |
|---|---|---|
| Мој Вардар (картичка) | нема | веднаш |
| Ваучер | нема | веднаш |
| Банкомат | според банката | до 15 минути |
| Продажно место | нема | веднаш |
| Пошта | 20 {DEN} | до 24 часа |

## Премин од припејд во постпејд

Преминот е бесплатен и бројот се задржува. Расположливиот кредит се пренесува како
одобрение на првата фактура. Со преминот се склучува договор и оттогаш важат
постпејд правилата, вклучително минималниот период и надоместокот за предвремено
раскинување. Преминот назад од постпејд во припејд е можен по истекот на
минималниот период.
""",
    )
    w(
        "prepaid/op-prepaid-topup-en.md",
        front("op-pripejd-dopolnuvanje", "Topping up credit", "en", C.CURRENT_YEAR, "prepaid")
        + f"""# Topping up prepaid credit

Minimum top-up {money(r['min_topup_mkd'])} MKD. Maximum balance
{money(r['max_balance_mkd'])} MKD; payments above that are rejected.

| Channel | Fee | Time to credit |
|---|---|---|
| My Vardar (card) | none | immediate |
| Voucher | none | immediate |
| ATM | per the bank | up to 15 minutes |
| Retail store | none | immediate |
| Post office | 20 MKD | up to 24 hours |

## Moving from prepaid to postpaid

The move is free and the number is kept. Remaining credit carries over as a credit
on the first invoice. The move creates a contract, so postpaid rules apply from that
point, including the minimum term and the early termination fee. Moving back to
prepaid is possible once the minimum term has expired.
""",
    )


# ─────────────────────────────────────────────────────────────────── billing
def gen_billing() -> None:
    """Worked invoice examples.

    Billing is the highest-volume real support category and the corpus had two
    documents for it. These are deliberately situation-shaped rather than
    topic-shaped: every one of them contains the words 'фактура', 'сметка' and
    'цена', so keyword overlap cannot separate them and the retriever has to
    match on the scenario. That is the useful kind of hard.

    All arithmetic is computed from PLANS, so no example can contradict a price
    list.
    """
    Y = C.CURRENT_YEAR
    fees = C.BILLING_FEES
    ct = C.CONTRACT_BY_YEAR[Y]
    by_code = {p.code: p for p in C.PLANS}

    def vat_split(gross: float) -> tuple[float, float]:
        net = gross / (1 + C.VAT_PCT / 100)
        return net, gross - net

    # ── 1. proration on activation, per plan
    for plan in C.PLANS:
        fee = plan.price[Y]
        day, days = 18, 30
        used = days - day + 1
        part = fee * used / days
        w(
            f"billing/op-smetka-proracun-aktivacija-{plan.code.lower()}-mk.md",
            front(
                f"op-smetka-proracun-aktivacija-{plan.code.lower()}",
                f"Пропорционална пресметка при активација — {plan.name}",
                "mk",
                Y,
                "billing",
            )
            + f"""# Пропорционална пресметка при активација
## {plan.name}

Пресметковниот период трае од 1 до {days} во месецот. Ако услугата е активирана на
{day}-ти, се наплаќаат {used} дена, не цел месец.

| Ставка | Пресметка | Износ |
|---|---|---|
| Месечна претплата | — | {money(fee)} {DEN} |
| Искористени денови | {used} од {days} | — |
| Пропорционален дел | {money(fee)} × {used} ÷ {days} | **{money(round(part, 2))} {DEN}** |

Износот е со вклучен ДДВ од {C.VAT_PCT}%.

## Што уште се појавува на истата фактура

Претплатата за следниот полн месец се наплаќа однапред, во истата фактура. Затоа
првата фактура вообичаено изнесува {money(round(part + fee, 2))} {DEN}, а не
{money(fee)} {DEN}. Ова не е грешка и не се повторува во наредните месеци.

## Ако услугата е активирана на 1-ви

Тогаш нема пропорционален дел и првата фактура е {money(fee)} {DEN}.
""",
        )
        w(
            f"billing/op-invoice-proration-activation-{plan.code.lower()}-en.md",
            front(
                f"op-smetka-proracun-aktivacija-{plan.code.lower()}",
                f"Proration on activation — {plan.name}",
                "en",
                Y,
                "billing",
            )
            + f"""# Proration on activation
## {plan.name}

The billing period runs from the 1st to the {days}th. If the service is activated on
the {day}th, {used} days are charged, not a full month.

| Item | Calculation | Amount |
|---|---|---|
| Monthly fee | — | {money(fee)} MKD |
| Days used | {used} of {days} | — |
| Prorated part | {money(fee)} × {used} ÷ {days} | **{money(round(part, 2))} MKD** |

Amounts include {C.VAT_PCT}% VAT.

## What else appears on the same invoice

The following full month is billed in advance on the same invoice. That is why the
first invoice usually comes to {money(round(part + fee, 2))} MKD rather than
{money(fee)} MKD. This is not an error and does not repeat.

## If the service is activated on the 1st

There is no prorated part and the first invoice is {money(fee)} MKD.
""",
        )

    # ── 2. mid-cycle upgrade, per adjacent pair
    pairs = [("S", "M"), ("M", "L"), ("L", "XL"), ("XL", "L")]
    for a, b in pairs:
        pa, pb = by_code[a], by_code[b]
        fa, fb = pa.price[Y], pb.price[Y]
        day, days = 12, 30
        rem = days - day + 1
        credit = fa * rem / days
        charge = fb * rem / days
        delta = charge - credit
        down = fb < fa
        floor_ok = fb >= fa * ct["downgrade_floor_pct"] / 100
        note_mk = (
            f"Ова е намалување на пакет. Дозволено е само ако новата претплата не е под "
            f"{ct['downgrade_floor_pct']}% од првичната. {money(fb)} наспроти "
            f"{money(round(fa * ct['downgrade_floor_pct'] / 100, 2))} {DEN} — "
            f"{'условот е исполнет' if floor_ok else 'условот НЕ е исполнет и барањето се одбива'}. "
            f"Намалувањето важи од следниот период, не веднаш."
            if down
            else "Ова е зголемување на пакет и важи веднаш."
        )
        note_en = (
            f"This is a downgrade. It is allowed only if the new fee is not below "
            f"{ct['downgrade_floor_pct']}% of the original. {money(fb)} against "
            f"{money(round(fa * ct['downgrade_floor_pct'] / 100, 2))} MKD, so the condition "
            f"{'is met' if floor_ok else 'is NOT met and the request is refused'}. "
            f"A downgrade takes effect from the next period, not immediately."
            if down
            else "This is an upgrade and takes effect immediately."
        )
        w(
            f"billing/op-smetka-promena-paket-{a.lower()}-{b.lower()}-mk.md",
            front(
                f"op-smetka-promena-paket-{a.lower()}-{b.lower()}",
                f"Промена на пакет во тек на период — {a} во {b}",
                "mk",
                Y,
                "billing",
            )
            + f"""# Промена од {pa.name} во {pb.name}
## Пресметка во тек на пресметковен период

Промената е побарана на {day}-ти. Преостануваат {rem} од {days} дена.

| Ставка | Пресметка | Износ |
|---|---|---|
| Одобрение за стариот пакет | {money(fa)} × {rem} ÷ {days} | −{money(round(credit, 2))} {DEN} |
| Наплата за новиот пакет | {money(fb)} × {rem} ÷ {days} | +{money(round(charge, 2))} {DEN} |
| Разлика на оваа фактура | — | **{'+' if delta >= 0 else '−'}{money(round(abs(delta), 2))} {DEN}** |
| Од следниот месец | — | {money(fb)} {DEN} |

{note_mk}

## Квота за интернет по промената

Квотата се пресметува пропорционално за преостанатите денови. Веќе потрошениот
сообраќај не се враќа и не се пренесува.
""",
        )
        w(
            f"billing/op-invoice-plan-change-{a.lower()}-{b.lower()}-en.md",
            front(
                f"op-smetka-promena-paket-{a.lower()}-{b.lower()}",
                f"Mid-cycle plan change — {a} to {b}",
                "en",
                Y,
                "billing",
            )
            + f"""# Change from {pa.name} to {pb.name}
## Calculation mid-period

The change is requested on the {day}th. {rem} of {days} days remain.

| Item | Calculation | Amount |
|---|---|---|
| Credit for the old plan | {money(fa)} × {rem} ÷ {days} | −{money(round(credit, 2))} MKD |
| Charge for the new plan | {money(fb)} × {rem} ÷ {days} | +{money(round(charge, 2))} MKD |
| Difference on this invoice | — | **{'+' if delta >= 0 else '−'}{money(round(abs(delta), 2))} MKD** |
| From next month | — | {money(fb)} MKD |

{note_en}

## Data allowance after the change

The allowance is prorated over the remaining days. Traffic already used is not
refunded and does not carry over.
""",
        )

    # ── 3. final invoice after termination, per plan
    for plan in C.PLANS:
        fee = plan.price[Y]
        remaining = 7
        early = fee * ct["early_fee_pct"] / 100 * remaining
        w(
            f"billing/op-smetka-poslednja-{plan.code.lower()}-mk.md",
            front(
                f"op-smetka-poslednja-{plan.code.lower()}",
                f"Последна фактура по раскинување — {plan.name}",
                "mk",
                Y,
                "billing",
            )
            + f"""# Последна фактура по раскинување
## {plan.name}, раскинување пред истек на минималниот период

Минималниот период за договори склучени во {Y} изнесува {ct['min_term_months']} месеци.
Во примерот преостануваат {remaining} месеци.

| Ставка | Пресметка | Износ |
|---|---|---|
| Претплата до денот на исклучување | пропорционално | според датумот |
| Надоместок за предвремено раскинување | {money(fee)} × {ct['early_fee_pct']}% × {remaining} | {money(round(early, 2))} {DEN} |
| Преостанати рати за уред | доспеваат веднаш | според договорот |
| Неискористено одобрение | се враќа | −износ |

Отказниот рок е {ct['notice_days']} дена. Претплатата се наплаќа до крајот на
отказниот рок дури и ако СИМ картичката веќе не се користи.

## Кога нема надоместок

Нема надоместок ако минималниот период е истечен, ако раскинувањето е во рок од
{ct['cooloff_days']} дена од склучувањето, или ако е поради еднострана измена на
условите од страна на операторот која е на штета на корисникот.
""",
        )
        w(
            f"billing/op-invoice-final-{plan.code.lower()}-en.md",
            front(
                f"op-smetka-poslednja-{plan.code.lower()}",
                f"Final invoice after termination — {plan.name}",
                "en",
                Y,
                "billing",
            )
            + f"""# Final invoice after termination
## {plan.name}, terminated before the minimum term ends

The minimum term for contracts signed in {Y} is {ct['min_term_months']} months.
In this example {remaining} months remain.

| Item | Calculation | Amount |
|---|---|---|
| Fee up to the disconnection date | prorated | per the date |
| Early termination fee | {money(fee)} × {ct['early_fee_pct']}% × {remaining} | {money(round(early, 2))} MKD |
| Remaining device instalments | fall due immediately | per the contract |
| Unused credit | refunded | −amount |

The notice period is {ct['notice_days']} days. The fee is charged to the end of the
notice period even if the SIM is no longer in use.

## When no fee applies

No fee applies if the minimum term has expired, if termination is within
{ct['cooloff_days']} days of signing, or if it follows a unilateral change of terms
by the operator that is to the customer's detriment.
""",
        )

    # ── 4. single-instance scenarios
    m = by_code["M"]
    fee = m.price[Y]
    net, vat = vat_split(fee)
    addon = C.DATA_ADDONS[1]
    pack = C.ROAMING_PACKS[0]

    singles: list[tuple[str, str, str, str, str]] = [
        (
            "op-smetka-fup",
            "Достигната квота и намалена брзина",
            "Fair use throttling on the invoice",
            f"""# Достигната квота

Кај {m.name} квотата за {Y} изнесува {m.data_gb[Y]} GB. По потрошената квота брзината
се намалува на {C.FUP['throttle_kbps']} kbps до крајот на периодот.

**Не се наплаќа ништо дополнително.** На фактурата нема ставка за пречекорување, затоа
што автоматската наплата по MB е исклучена по правило. Ако на фактурата се појави
ставка за сообраќај над квотата, тоа значи дека опцијата „Продолжи со полна брзина"
била рачно вклучена во Мој Вардар.

| Ставка | Износ |
|---|---|
| Месечна претплата | {money(fee)} {DEN} |
| Сообраќај над квотата | 0,00 {DEN} |
| Вкупно | {money(fee)} {DEN} |

Алтернатива на намалената брзина е додатен пакет: {addon['gb']} GB за
{money(addon['price'][Y])} {DEN}, важи {addon['days']} дена.""",
            f"""# Allowance reached

On {m.name} the {Y} allowance is {m.data_gb[Y]} GB. Once it is used, the speed is
reduced to {C.FUP['throttle_kbps']} kbps until the end of the period.

**Nothing extra is charged.** There is no overage line on the invoice, because
automatic per-MB charging is off by default. If an over-allowance line does appear,
the "Continue at full speed" option was switched on manually in My Vardar.

| Item | Amount |
|---|---|
| Monthly fee | {money(fee)} MKD |
| Traffic over the allowance | 0.00 MKD |
| Total | {money(fee)} MKD |

The alternative to throttling is an add-on: {addon['gb']} GB for
{money(addon['price'][Y])} MKD, valid {addon['days']} days.""",
        ),
        (
            "op-smetka-ddv",
            "Пресметка на ДДВ на фактура",
            "VAT breakdown on the invoice",
            f"""# Пресметка на ДДВ

Сите објавени цени се **со вклучен ДДВ** од {C.VAT_PCT}%. На фактурата износот се
прикажува расчленето, што често изгледа како двојна наплата иако не е.

| Ставка | Износ |
|---|---|
| Основица | {money(round(net, 2))} {DEN} |
| ДДВ {C.VAT_PCT}% | {money(round(vat, 2))} {DEN} |
| **Вкупно за плаќање** | **{money(fee)} {DEN}** |

Основицата се добива со делење на бруто износот со {1 + C.VAT_PCT / 100:.2f}, а не со
одземање на {C.VAT_PCT}%. Тоа е најчестата грешка при проверка на фактура.

Правни лица со ДДВ број добиваат фактура со истиот вкупен износ; разликата е само во
можноста за одбивање на претходниот данок.""",
            f"""# VAT breakdown

All published prices **include** {C.VAT_PCT}% VAT. The invoice shows the amount split
out, which often looks like double charging but is not.

| Item | Amount |
|---|---|
| Net | {money(round(net, 2))} MKD |
| VAT {C.VAT_PCT}% | {money(round(vat, 2))} MKD |
| **Total payable** | **{money(fee)} MKD** |

The net figure is obtained by dividing the gross by {1 + C.VAT_PCT / 100:.2f}, not by
subtracting {C.VAT_PCT}%. That is the most common mistake when checking an invoice.

VAT-registered businesses receive an invoice with the same total; the only difference
is their ability to reclaim input tax.""",
        ),
        (
            "op-smetka-ednokratni",
            "Еднократни надоместоци",
            "One-off charges",
            f"""# Еднократни надоместоци

| Надоместок | Износ | Кога се наплаќа |
|---|---|---|
| Замена на СИМ картичка | {money(fees['sim_replacement'])} {DEN} | при губење или оштетување |
| Печатена фактура по пошта | {money(fees['paper_invoice'])} {DEN} месечно | ако не е избрана е-фактура |
| Повторно вклучување по суспензија | {money(fees['reconnection'])} {DEN} | по подмирен долг |
| Детална спецификација на повици | {money(fees['itemised_bill'])} {DEN} | на барање |
| Пренос на број кон друг оператор | 0 {DEN} | секогаш бесплатно |

Замената на СИМ е бесплатна ако е поради технички дефект на картичката потврден во
продажно место, или при премин на eSIM во првите 30 дена од активација.""",
            f"""# One-off charges

| Charge | Amount | When it applies |
|---|---|---|
| SIM replacement | {money(fees['sim_replacement'])} MKD | loss or damage |
| Paper invoice by post | {money(fees['paper_invoice'])} MKD per month | if e-invoice is not selected |
| Reconnection after suspension | {money(fees['reconnection'])} MKD | after the debt is settled |
| Itemised call listing | {money(fees['itemised_bill'])} MKD | on request |
| Porting the number out | 0 MKD | always free |

SIM replacement is free if it follows a technical fault confirmed in store, or when
switching to eSIM within the first 30 days of activation.""",
        ),
        (
            "op-smetka-docna-uplata",
            "Задоцнето плаќање, суспензија и повторно вклучување",
            "Late payment, suspension and reconnection",
            f"""# Задоцнето плаќање

Рокот за плаќање е 15 дена од датумот на фактурата.

| Ден по достасување | Што се случува |
|---|---|
| 1 | Потсетување со SMS. Нема камата. |
| 15 | Затезна камата {fees['late_payment_pct']}% месечно на доспеаниот износ |
| {fees['suspension_after_days']} | Суспензија на одлезни повици и интернет. Дојдовните остануваат. |
| {fees['termination_after_days']} | Раскинување на договорот и пренос во наплата |

Повторното вклучување чини {money(fees['reconnection'])} {DEN} и се врши во рок од 2
часа по евидентирана уплата.

## Ако износот е оспорен

Ако е поднесен приговор во рок од {C.COMPLAINTS['submit_within_days']} дена,
**оспорениот дел не се наплаќа** додека трае постапката и не се пресметува камата на
него. Неоспорениот дел останува достасан. Суспензија поради неплатен оспорен износ не
е дозволена.""",
            f"""# Late payment

Payment is due 15 days from the invoice date.

| Day past due | What happens |
|---|---|
| 1 | SMS reminder. No interest. |
| 15 | Default interest of {fees['late_payment_pct']}% per month on the overdue amount |
| {fees['suspension_after_days']} | Outgoing calls and data suspended. Incoming stays on. |
| {fees['termination_after_days']} | Contract terminated and the debt passed to collection |

Reconnection costs {money(fees['reconnection'])} MKD and is done within 2 hours of the
payment being recorded.

## If the amount is disputed

If a complaint is filed within {C.COMPLAINTS['submit_within_days']} days, **the
disputed part is not collected** while the case is open and no interest accrues on it.
The undisputed part remains due. Suspension for an unpaid disputed amount is not
permitted.""",
        ),
        (
            "op-smetka-odobrenie",
            "Одобрение по прифатен приговор",
            "Credit note after an upheld complaint",
            f"""# Одобрение по прифатен приговор

Кога приговорот е прифатен, износот не се враќа во готово по правило. Се книжи како
одобрение на наредната фактура.

| Ставка | Износ |
|---|---|
| Месечна претплата | {money(fee)} {DEN} |
| Одобрение по приговор бр. 2026/0417 | −{money(round(fee * 0.4, 2))} {DEN} |
| **За плаќање** | **{money(round(fee * 0.6, 2))} {DEN}** |

## Кога се враќа во готово

Враќање на сметка се врши ако договорот е раскинат, ако одобрението надминува две
месечни претплати, или на изречно барање на корисникот. Рокот е
{C.COMPLAINTS['refund_days']} дена од прифаќањето на приговорот.

Одобрението секогаш носи број на приговорот, за да може да се поврзе со постапката.""",
            f"""# Credit note after an upheld complaint

When a complaint is upheld the amount is not refunded in cash by default. It is posted
as a credit on the next invoice.

| Item | Amount |
|---|---|
| Monthly fee | {money(fee)} MKD |
| Credit for complaint no. 2026/0417 | −{money(round(fee * 0.4, 2))} MKD |
| **Payable** | **{money(round(fee * 0.6, 2))} MKD** |

## When cash is refunded

A bank refund is made if the contract has been terminated, if the credit exceeds two
monthly fees, or on the customer's explicit request. The deadline is
{C.COMPLAINTS['refund_days']} days from the complaint being upheld.

The credit always carries the complaint number so it can be traced to the case.""",
        ),
        (
            "op-smetka-rata-uredj",
            "Рата за уред на фактура",
            "Device instalment on the invoice",
            f"""# Рата за уред на фактура

Уредот купен на рати се појавува како посебна ставка, одвоена од претплатата.

| Ставка | Износ |
|---|---|
| Месечна претплата ({m.name}) | {money(fee)} {DEN} |
| Рата за уред, 8 од 24 | {money(1250)} {DEN} |
| **Вкупно** | **{money(fee + 1250)} {DEN}** |

Ратата не се менува при промена на тарифен пакет. Раскинувањето на договорот за
услуга **не** го гаси договорот за уред: преостанатите рати доспеваат веднаш и се
наплаќаат во една ставка на последната фактура.

Предвремена отплата на уредот е можна во секое време без надоместок; преостанатата
главнина се пресметува линеарно.""",
            f"""# Device instalment on the invoice

A device bought on instalments appears as a separate line, apart from the service fee.

| Item | Amount |
|---|---|
| Monthly fee ({m.name}) | {money(fee)} MKD |
| Device instalment, 8 of 24 | {money(1250)} MKD |
| **Total** | **{money(fee + 1250)} MKD** |

The instalment does not change when the tariff changes. Terminating the service
contract does **not** cancel the device agreement: the remaining instalments fall due
immediately and appear as a single line on the final invoice.

The device can be paid off early at any time without a fee; the outstanding principal
is calculated on a straight-line basis.""",
        ),
        (
            "op-smetka-dodatok",
            "Купен додатен интернет пакет во тек на период",
            "Add-on purchased mid-cycle",
            f"""# Додатен интернет пакет на фактура

Додатните пакети се наплаќаат во целост во месецот на купување. Нема пропорционална
пресметка, затоа што важноста тече од моментот на активација, не од почетокот на
пресметковниот период.

| Ставка | Износ |
|---|---|
| Месечна претплата ({m.name}) | {money(fee)} {DEN} |
| Додаток {addon['gb']} GB, {addon['days']} дена | {money(addon['price'][Y])} {DEN} |
| **Вкупно** | **{money(fee + addon['price'][Y])} {DEN}** |

Неискористениот сообраќај од додатокот **не се пренесува** во нареден период и не се
рефундира по истек на важноста.

Редослед на трошење: прво домашната квота, потоа додатоците по редослед на истекување.""",
            f"""# Data add-on on the invoice

Add-ons are charged in full in the month of purchase. There is no proration, because
validity runs from activation rather than from the start of the billing period.

| Item | Amount |
|---|---|
| Monthly fee ({m.name}) | {money(fee)} MKD |
| {addon['gb']} GB add-on, {addon['days']} days | {money(addon['price'][Y])} MKD |
| **Total** | **{money(fee + addon['price'][Y])} MKD** |

Unused data from an add-on does **not** carry over and is not refunded when the
validity expires.

Consumption order: the domestic allowance first, then add-ons in order of expiry.""",
        ),
        (
            "op-smetka-roaming-wb6",
            "Роаминг во Западен Балкан на фактура",
            "Western Balkans roaming on the invoice",
            f"""# Роаминг во Западен Балкан на фактура

Пример: 6 дена во Србија, 4,2 GB, 96 минути, 30 SMS, постпејд {m.name}.

| Ставка | Износ |
|---|---|
| Месечна претплата | {money(fee)} {DEN} |
| Интернет во роаминг, Србија, 4,2 GB | 0,00 {DEN} |
| Повици во роаминг, 96 мин | 0,00 {DEN} |
| SMS во роаминг, 30 | 0,00 {DEN} |
| **Вкупно** | **{money(fee)} {DEN}** |

Србија е во зоната на Западен Балкан, каде важи наплата како во домашна мрежа.
Потрошениот сообраќај се одзема од домашната квота од {m.data_gb[Y]} GB и **не се
појавува како посебна ставка**.

## Честа забуна

Ако на фактурата се појави ставка за роаминг во Србија, проверете ја земјата на
мрежата, не земјата на дестинацијата. Повик од Србија кон Албанија е меѓународен
повик направен во роаминг и се наплаќа, иако двете земји се во истата зона.

Оваа зона не е иста како ЕУ. За Грција важат други правила.""",
            f"""# Western Balkans roaming on the invoice

Example: 6 days in Serbia, 4.2 GB, 96 minutes, 30 SMS, postpaid {m.name}.

| Item | Amount |
|---|---|
| Monthly fee | {money(fee)} MKD |
| Roaming data, Serbia, 4.2 GB | 0.00 MKD |
| Roaming calls, 96 min | 0.00 MKD |
| Roaming SMS, 30 | 0.00 MKD |
| **Total** | **{money(fee)} MKD** |

Serbia is in the Western Balkans zone, where domestic rates apply. The traffic is
deducted from the domestic {m.data_gb[Y]} GB allowance and **does not appear as a
separate line**.

## Common confusion

If a Serbia roaming line does appear, check the network country rather than the
destination country. A call from Serbia to Albania is an international call made while
roaming and is charged, even though both countries are in the same zone.

This zone is not the same as the EU. Different rules apply to Greece.""",
        ),
        (
            "op-smetka-roaming-eu",
            "Роаминг во ЕУ на фактура",
            "EU roaming on the invoice",
            f"""# Роаминг во ЕУ на фактура

Пример: 5 дена во Грција, 3,1 GB, постпејд {m.name}.

Северна Македонија не е членка на ЕУ, па правилото „роаминг како дома" на Унијата
**не се применува** за македонски број во Грција. Важи ограничена наплата по MB со
месечен лимит.

| Ставка | Пресметка | Износ |
|---|---|---|
| Месечна претплата | — | {money(fee)} {DEN} |
| Интернет во роаминг, ЕУ, 3,1 GB | по важечка тарифа за зона 2 | се наплаќа |
| Месечен лимит на трошок | автоматска блокада | {money(C.FUP['roaming_monthly_cap_mkd'])} {DEN} |

Поевтина алтернатива е пакет за роаминг: {pack['gb']} GB за
{money(pack['price'][Y])} {DEN}, важи {pack['days']} дена. Пакетот мора да се активира
**пред** почетокот на трошењето; не се применува наназад на веќе потрошен сообраќај.

## Зошто Србија е бесплатна а Грција не

Србија е во зоната на Западен Балкан по регионален договор. Грција е во ЕУ, каде
реципроцитетот важи меѓу членки. Двете се соседни земји и двете имаат различен режим.""",
            f"""# EU roaming on the invoice

Example: 5 days in Greece, 3.1 GB, postpaid {m.name}.

North Macedonia is not an EU member, so the Union's roam-like-at-home rule **does not
apply** to a Macedonian number in Greece. Capped per-MB charging applies instead, with
a monthly ceiling.

| Item | Calculation | Amount |
|---|---|---|
| Monthly fee | — | {money(fee)} MKD |
| Roaming data, EU, 3.1 GB | at the zone 2 tariff | charged |
| Monthly spend cap | automatic bar | {money(C.FUP['roaming_monthly_cap_mkd'])} MKD |

A roaming pack is cheaper: {pack['gb']} GB for {money(pack['price'][Y])} MKD, valid
{pack['days']} days. The pack must be activated **before** usage starts; it is not
applied retrospectively to traffic already used.

## Why Serbia is free and Greece is not

Serbia is in the Western Balkans zone under a regional agreement. Greece is in the EU,
where reciprocity applies between member states. Two neighbouring countries, two
different regimes.""",
        ),
        (
            "op-smetka-roaming-svet",
            "Меѓународен роаминг на фактура",
            "International roaming on the invoice",
            f"""# Меѓународен роаминг на фактура

Пример: 3 дена во Турција, 1,4 GB, постпејд {m.name}.

Турција не е ни во ЕУ ни во зоната на Западен Балкан. Важи полна меѓународна тарифа
за зона 3.

| Ставка | Износ |
|---|---|
| Месечна претплата | {money(fee)} {DEN} |
| Интернет во роаминг, зона 3, 1,4 GB | по тарифа за зона 3 |
| Месечен лимит на трошок | {money(C.FUP['roaming_monthly_cap_mkd'])} {DEN} |

По достигнување на лимитот интернетот се блокира и се испраќа SMS. Блокадата може да
се укине рачно во Мој Вардар, со што корисникот прифаќа наплата над лимитот.

## Три соседни земји, три режима

| Земја | Зона | Наплата |
|---|---|---|
| Србија | Западен Балкан | како дома |
| Грција | ЕУ | ограничена по MB |
| Турција | меѓународна | полна тарифа |

Ова е најчестиот извор на неочекувано висока фактура. Препорачано е пакетот за
роаминг да се купи пред патувањето.""",
            f"""# International roaming on the invoice

Example: 3 days in Turkey, 1.4 GB, postpaid {m.name}.

Turkey is neither in the EU nor in the Western Balkans zone. The full international
zone 3 tariff applies.

| Item | Amount |
|---|---|
| Monthly fee | {money(fee)} MKD |
| Roaming data, zone 3, 1.4 GB | at the zone 3 tariff |
| Monthly spend cap | {money(C.FUP['roaming_monthly_cap_mkd'])} MKD |

Once the cap is reached data is barred and an SMS is sent. The bar can be lifted
manually in My Vardar, which means accepting charges above the cap.

## Three neighbouring countries, three regimes

| Country | Zone | Charging |
|---|---|---|
| Serbia | Western Balkans | as at home |
| Greece | EU | capped per MB |
| Turkey | international | full tariff |

This is the most common source of an unexpectedly high invoice. Buying a roaming pack
before travelling is recommended.""",
        ),
        (
            "op-smetka-kako-se-cita",
            "Како се чита фактурата",
            "How to read the invoice",
            f"""# Како се чита фактурата

Фактурата има четири дела. Прочитани по ред, објаснуваат речиси секое отстапување.

**1. Заглавие.** Број на фактура, пресметковен период, датум на достасување. Периодот
не се совпаѓа со календарскиот месец ако услугата е активирана во тек на месецот.

**2. Претплата.** Секогаш **однапред**, за периодот што доаѓа.

**3. Потрошувачка.** Секогаш **наназад**, за периодот што помина. Оваа разлика е
причината зошто фактурата покрива два различни временски интервали и зошто роаминг од
минатиот месец се појавува дури сега.

**4. Еднократни ставки.** Рати, надоместоци, одобренија.

## Проверка во три чекора

1. Дали претплатата одговара на пакетот во Мој Вардар?
2. Дали има ставка што не ја препознавате? Проверете го датумот, не износот.
3. Дали збирот на ставките одговара на вкупниот износ со ДДВ?

Ако некој чекор не се совпаѓа, поднесете приговор во рок од
{C.COMPLAINTS['submit_within_days']} дена од датумот на фактурата.""",
            f"""# How to read the invoice

The invoice has four parts. Read in order, they explain almost every discrepancy.

**1. Header.** Invoice number, billing period, due date. The period does not match the
calendar month if the service was activated mid-month.

**2. Subscription.** Always **in advance**, for the period ahead.

**3. Usage.** Always **in arrears**, for the period just ended. This difference is why
an invoice covers two different time spans, and why last month's roaming only appears
now.

**4. One-off items.** Instalments, fees, credits.

## A three-step check

1. Does the subscription match the plan shown in My Vardar?
2. Is there a line you do not recognise? Check the date, not the amount.
3. Does the sum of the lines match the VAT-inclusive total?

If any step does not reconcile, file a complaint within
{C.COMPLAINTS['submit_within_days']} days of the invoice date.""",
        ),
    ]

    for doc_id, title_mk, title_en, body_mk, body_en in singles:
        slug = doc_id.replace("op-smetka-", "")
        w(
            f"billing/{doc_id}-mk.md",
            front(doc_id, title_mk, "mk", Y, "billing") + body_mk + "\n",
        )
        w(
            f"billing/op-invoice-{slug}-en.md",
            front(doc_id, title_en, "en", Y, "billing") + body_en + "\n",
        )


# ────────────────────────────────────────────────────── complaints, SLA, credits
def gen_complaints() -> None:
    """Complaints, service levels and compensation.

    Zero coverage before this, and it is the natural bridge between the operator
    layer and the regulation layer: these deadlines are the operator's
    implementation of obligations that live in the EU documents. A question about
    them is answerable from either layer, so the eval can check *which* source the
    model cites, not just whether the answer is right.
    """
    Y = C.CURRENT_YEAR
    cm = C.COMPLAINTS
    reg_mk, reg_en = cm["regulator"]["mk"], cm["regulator"]["en"]

    w(
        "complaints/op-prigovor-postapka-mk.md",
        front("op-prigovor-postapka", "Приговор — постапка и рокови", "mk", Y, "complaints")
        + f"""# Приговор
## Постапка и рокови

Приговор може да поднесе секој корисник на услугата, за фактура, за квалитет на
услугата или за постапување на операторот.

| Чекор | Рок |
|---|---|
| Поднесување на приговор | {cm['submit_within_days']} дена од датумот на фактурата или од настанот |
| Одговор на операторот | {cm['operator_reply_days']} дена од приемот |
| Одговор кај сложени предмети | {cm['operator_reply_days_complex']} дена, со писмено известување за одложувањето |
| Ескалација кон {reg_mk} | {cm['escalate_to_regulator_days']} дена по одговорот на операторот |
| Враќање на средства | {cm['refund_days']} дена од прифаќањето |

## Канали за поднесување

{chr(10).join(f'- {c}' for c in cm['channels_mk'])}

Секој поднесен приговор добива број. Без број приговорот не е евидентиран, што е
најчестата причина зошто корисникот тврди дека поднел а операторот нема евиденција.
Барајте потврда со број при поднесување преку телефон.

## Оспорен износ

Додека трае постапката **оспорениот дел не се наплаќа** и на него не тече затезна
камата. Неоспорениот дел останува достасан и мора да се плати во редовниот рок.
Суспензија на услугата поради неплатен оспорен износ не е дозволена.

## Ако одговорот не е задоволителен

Корисникот има право да го однесе предметот пред {reg_mk} во рок од
{cm['escalate_to_regulator_days']} дена. Постапката пред регулаторот е бесплатна за
корисникот. Правото на судска заштита останува независно од оваа постапка.

## Што треба да содржи приговорот

Име и број на корисник, број на фактура или датум на настанот, што конкретно се
оспорува, износ ако е применливо, и барање. Приговор без наведен износ или конкретно
барање се обработува, но одговорот е неминовно поопшт.
""",
    )
    w(
        "complaints/op-complaint-procedure-en.md",
        front("op-prigovor-postapka", "Complaints — procedure and deadlines", "en", Y, "complaints")
        + f"""# Complaints
## Procedure and deadlines

Any customer may file a complaint about an invoice, service quality, or the
operator's conduct.

| Step | Deadline |
|---|---|
| Filing a complaint | {cm['submit_within_days']} days from the invoice date or the event |
| Operator's reply | {cm['operator_reply_days']} days from receipt |
| Reply in complex cases | {cm['operator_reply_days_complex']} days, with written notice of the delay |
| Escalation to {reg_en} | {cm['escalate_to_regulator_days']} days after the operator's reply |
| Refund | {cm['refund_days']} days from the complaint being upheld |

## Channels

{chr(10).join(f'- {c}' for c in cm['channels_en'])}

Every complaint receives a reference number. Without one it is not on record, which is
the most common reason a customer insists they filed and the operator has no trace.
Ask for the number when filing by phone.

## Disputed amounts

While the case is open the **disputed part is not collected** and no default interest
accrues on it. The undisputed part remains due and must be paid normally. Suspending
service over an unpaid disputed amount is not permitted.

## If the reply is unsatisfactory

The customer may take the case to {reg_en} within
{cm['escalate_to_regulator_days']} days. The regulator's procedure is free for the
customer. The right to go to court is independent of it.

## What a complaint should contain

Name and customer number, invoice number or date of the event, what specifically is
disputed, the amount where applicable, and what is being asked for. A complaint with
no stated amount or specific request is still processed, but the reply is necessarily
more general.
""",
    )

    # ── SLA targets
    rows_mk = "\n".join(
        f"| {s} | {t} | {win} | {cr}% |" for s, t, win, cr in C.SLA
    )
    sla_en = [
        ("Mobile network availability", "99.5%", "monthly", 5),
        ("Mobile data availability", "99.0%", "monthly", 5),
        ("Fault clearance, urban", "24 hours", "from report", 10),
        ("Fault clearance, rural", "72 hours", "from report", 10),
        ("New SIM activation", "2 hours", "from signature", 0),
        ("Number porting", "1 working day", "from request", 15),
        ("Complaint response", "15 days", "from receipt", 0),
    ]
    rows_en = "\n".join(f"| {s} | {t} | {win} | {cr}% |" for s, t, win, cr in sla_en)

    w(
        "complaints/op-nivo-usluga-mk.md",
        front("op-nivo-usluga", "Гарантирано ниво на услуга", "mk", Y, "complaints")
        + f"""# Гарантирано ниво на услуга

| Услуга | Цел | Мерење | Одобрение ако не е исполнето |
|---|---|---|---|
{rows_mk}

Одобрението се изразува како процент од месечната претплата и се книжи автоматски на
наредната фактура кога отстапувањето е евидентирано во системот на операторот.

## Кога одобрението не се доделува автоматски

Ако прекинот не е евидентиран, корисникот мора да го пријави. Пријавата треба да
содржи датум, време и локација. Одобрение по пријава се доделува само ако прекинот
може да се потврди во логовите на мрежата.

## Исклучоци

Планираните работи најавени најмалку 48 часа однапред не се сметаат за прекин, под
услов да траат помалку од 6 часа и да се во периодот меѓу 01:00 и 06:00. Прекини
поради виша сила, прекин на електрична енергија кај корисникот, или оштетување
предизвикано од трето лице не влегуваат во пресметката.
""",
    )
    w(
        "complaints/op-service-levels-en.md",
        front("op-nivo-usluga", "Guaranteed service levels", "en", Y, "complaints")
        + f"""# Guaranteed service levels

| Service | Target | Measurement | Credit if missed |
|---|---|---|---|
{rows_en}

The credit is expressed as a percentage of the monthly fee and is applied
automatically to the next invoice when the shortfall is recorded in the operator's
systems.

## When the credit is not automatic

If an outage was not recorded, the customer must report it. The report should include
date, time and location. A credit is granted on report only if the outage can be
confirmed in the network logs.

## Exclusions

Planned work announced at least 48 hours in advance is not counted as an outage,
provided it lasts under 6 hours and falls between 01:00 and 06:00. Outages caused by
force majeure, a power cut at the customer's premises, or third-party damage are
excluded.
""",
    )

    # ── outage compensation table
    rows_mk = "\n".join(
        f"| {a} — {'над ' + str(a) if b > 1000 else b} часа | {pct}% од месечната претплата |"
        for a, b, pct in C.OUTAGE_CREDIT
    )
    rows_en = "\n".join(
        f"| {a} — {'over ' + str(a) if b > 1000 else b} hours | {pct}% of the monthly fee |"
        for a, b, pct in C.OUTAGE_CREDIT
    )
    ex = C.PLANS[1]
    w(
        "complaints/op-nadomest-prekin-mk.md",
        front("op-nadomest-prekin", "Надомест за прекин на услуга", "mk", Y, "complaints")
        + f"""# Надомест за прекин на услуга

| Времетраење на прекинот | Одобрение |
|---|---|
{rows_mk}

Прекин пократок од 4 часа не носи одобрение.

## Пример

{ex.name}, месечна претплата {money(ex.price[Y])} {DEN}, прекин од 30 часа.
Тоа паѓа во опсегот 24 до 72 часа, значи 40%.

{money(ex.price[Y])} × 40% = **{money(round(ex.price[Y] * 0.4, 2))} {DEN}** одобрение
на наредната фактура.

## Кумулација

Повеќе прекини во ист месец се собираат по времетраење, не по број. Три прекина од по
5 часа се третираат како еден прекин од 15 часа, што дава 15%, а не три пати по 5%.

Вкупното одобрение во еден месец не може да надмине 100% од месечната претплата.
Барање над тој износ се разгледува како барање за надомест на штета и излегува од
оваа постапка.
""",
    )
    w(
        "complaints/op-outage-compensation-en.md",
        front("op-nadomest-prekin", "Compensation for service outages", "en", Y, "complaints")
        + f"""# Compensation for service outages

| Outage duration | Credit |
|---|---|
{rows_en}

An outage shorter than 4 hours carries no credit.

## Example

{ex.name}, monthly fee {money(ex.price[Y])} MKD, a 30-hour outage. That falls in the
24 to 72 hour band, so 40%.

{money(ex.price[Y])} × 40% = **{money(round(ex.price[Y] * 0.4, 2))} MKD** credited on
the next invoice.

## Accumulation

Multiple outages in one month are added by duration, not by count. Three five-hour
outages are treated as one fifteen-hour outage, giving 15%, not three times 5%.

Total credit in one month cannot exceed 100% of the monthly fee. A claim beyond that
is treated as a damages claim and falls outside this procedure.
""",
    )

    # ── billing dispute specifics
    w(
        "complaints/op-prigovor-smetka-mk.md",
        front("op-prigovor-smetka", "Приговор на фактура", "mk", Y, "complaints")
        + f"""# Приговор на фактура

## Што се проверува

Операторот е должен да ги достави податоците врз основа на кои е составена спорната
ставка: датум, време, времетраење, мрежа и применета тарифа. Барањето за овие податоци
е бесплатно и не е посебна постапка.

## Товар на докажување

Доказот дека услугата е дадена и правилно наплатена е на страна на операторот.
Корисникот не мора да докажува дека не ја користел услугата. Ова е важно кај спорни
роаминг ставки, каде корисникот често нема свои записи.

## Најчести основани приговори

| Основ | Како се потврдува |
|---|---|
| Наплатен роаминг во зона со наплата како дома | се проверува мрежата, не земјата |
| Двојно наплатен додатен пакет | се бараат логовите на активација |
| Претплата наплатена по раскинување | се проверува датумот на исклучување |
| Наплата по MB иако опцијата не е вклучена | се проверува статусот на опцијата |
| Рата за уред по предвремена отплата | се проверува уплатата |

## Најчести неосновани приговори

Прва фактура повисока од очекуваното поради претплата однапред. Роаминг во ЕУ
наплатен затоа што македонски број нема право на „роаминг како дома" во Унијата.
Потрошена квота поради автоматско ажурирање на апликации.

Во двата случаја одговорот содржи пресметка, не само заклучок.
""",
    )
    w(
        "complaints/op-billing-dispute-en.md",
        front("op-prigovor-smetka", "Disputing an invoice", "en", Y, "complaints")
        + f"""# Disputing an invoice

## What gets checked

The operator must supply the data the disputed line was built from: date, time,
duration, network and the tariff applied. Requesting this data is free and is not a
separate procedure.

## Burden of proof

Proving that the service was delivered and correctly charged rests with the operator.
The customer does not have to prove they did not use it. This matters for disputed
roaming lines, where the customer usually has no records of their own.

## Complaints most often upheld

| Ground | How it is verified |
|---|---|
| Roaming charged in a domestic-rate zone | check the network, not the country |
| Add-on charged twice | pull the activation logs |
| Fee charged after termination | check the disconnection date |
| Per-MB charging with the option switched off | check the option's status |
| Device instalment after early settlement | check the payment |

## Complaints most often rejected

A first invoice higher than expected because the fee is billed in advance. EU roaming
charged because a Macedonian number has no roam-like-at-home right in the Union. An
allowance used up by automatic app updates.

In each case the reply contains the calculation, not just the conclusion.
""",
    )


# ────────────────────────────────────────────────────── contract terms by year
def gen_contract_terms() -> None:
    """Contract terms, one document per plan per year.

    The values genuinely differ between years, so 'what is the early termination
    fee' has three defensible answers and only the in_force one is correct. This
    makes effective_date filtering testable rather than decorative: without it,
    retrieval on topic alone will happily return the 2024 terms.
    """
    for plan in C.PLANS:
        for y in C.YEARS:
            ct = C.CONTRACT_BY_YEAR[y]
            fee = plan.price[y]
            rem = 10
            early = fee * ct["early_fee_pct"] / 100 * rem
            changed_mk, changed_en = [], []
            if y > C.YEARS[0]:
                prev = C.CONTRACT_BY_YEAR[y - 1]
                for k, label_mk, label_en in (
                    ("min_term_months", "минимален период", "minimum term"),
                    ("notice_days", "отказен рок", "notice period"),
                    ("early_fee_pct", "надоместок за раскинување", "early termination fee"),
                    ("sim_lock_months", "заклучување на уред", "device lock"),
                    ("downgrade_floor_pct", "праг за намалување", "downgrade floor"),
                ):
                    if prev[k] != ct[k]:
                        changed_mk.append(f"- {label_mk}: {prev[k]} → {ct[k]}")
                        changed_en.append(f"- {label_en}: {prev[k]} → {ct[k]}")
            diff_mk = (
                "\n## Изменето во однос на " + str(y - 1) + "\n\n" + "\n".join(changed_mk) + "\n"
                if changed_mk
                else ""
            )
            diff_en = (
                "\n## Changed from " + str(y - 1) + "\n\n" + "\n".join(changed_en) + "\n"
                if changed_en
                else ""
            )

            w(
                f"contract/op-dogovor-{plan.code.lower()}-{y}-mk.md",
                front(
                    f"op-dogovor-{plan.code.lower()}-{y}",
                    f"Договорни услови — {plan.name} ({y})",
                    "mk",
                    y,
                    "contract",
                )
                + f"""# Договорни услови
## {plan.name}, договори склучени во {y}

Овие услови важат за договори склучени од 1 јануари {y}. Договорите склучени порано
остануваат под условите важечки на денот на потпис.

| Услов | Вредност |
|---|---|
| Минимален договорен период | {ct['min_term_months']} месеци |
| Отказен рок | {ct['notice_days']} дена |
| Надоместок за предвремено раскинување | {ct['early_fee_pct']}% од месечната претплата по преостанат месец |
| Право на откажување без причина | {ct['cooloff_days']} дена од потпис |
| Праг за намалување на пакет | {ct['downgrade_floor_pct']}% од првичната претплата |
| Заклучување на уред за мрежа | {ct['sim_lock_months']} месеци |
| Автоматско продолжување | {'да, на неопределено време' if ct['auto_renew'] else 'не, преминува во месечен режим без обврска'} |
{diff_mk}
## Пример за пресметка

Месечна претплата {money(fee)} {DEN}, преостануваат {rem} месеци:

{money(fee)} × {ct['early_fee_pct']}% × {rem} = **{money(round(early, 2))} {DEN}**

## Кога надоместокот не се наплаќа

- по истек на минималниот период
- при раскинување во рок од {ct['cooloff_days']} дена од потпис
- при еднострана измена на условите на штета на корисникот
- при преселба во подрачје без покриеност, со доказ
- при смрт на корисникот

Ратите за уред не се дел од овој надоместок и доспеваат одделно.
""",
            )
            w(
                f"contract/op-contract-{plan.code.lower()}-{y}-en.md",
                front(
                    f"op-dogovor-{plan.code.lower()}-{y}",
                    f"Contract terms — {plan.name} ({y})",
                    "en",
                    y,
                    "contract",
                )
                + f"""# Contract terms
## {plan.name}, contracts signed in {y}

These terms apply to contracts signed from 1 January {y}. Earlier contracts remain
under the terms in force on the day of signature.

| Term | Value |
|---|---|
| Minimum term | {ct['min_term_months']} months |
| Notice period | {ct['notice_days']} days |
| Early termination fee | {ct['early_fee_pct']}% of the monthly fee per remaining month |
| Right of withdrawal | {ct['cooloff_days']} days from signature |
| Downgrade floor | {ct['downgrade_floor_pct']}% of the original fee |
| Device network lock | {ct['sim_lock_months']} months |
| Automatic renewal | {'yes, indefinite' if ct['auto_renew'] else 'no, reverts to a monthly rolling basis'} |
{diff_en}
## Worked example

Monthly fee {money(fee)} MKD, {rem} months remaining:

{money(fee)} × {ct['early_fee_pct']}% × {rem} = **{money(round(early, 2))} MKD**

## When no fee applies

- after the minimum term has expired
- on termination within {ct['cooloff_days']} days of signature
- on a unilateral change of terms to the customer's detriment
- on relocation to an area without coverage, with evidence
- on the death of the customer

Device instalments are not part of this fee and fall due separately.
""",
            )


# ──────────────────────────────────────────────────────────────── add-on packs
def gen_addons() -> None:
    """Data add-ons and roaming packs, one sheet per pack per year.

    Small, near-identical, numeric documents. Exactly the shape that defeats
    retrieval on topic and rewards metadata filtering plus a structured tool,
    which is the point being demonstrated.
    """
    for a in C.DATA_ADDONS:
        for y in C.YEARS:
            price = a["price"][y]
            per_gb = price / a["gb"]
            prev = (
                f"\nЦената во {y-1} изнесуваше {money(a['price'][y-1])} {DEN}.\n"
                if y > C.YEARS[0]
                else "\n"
            )
            w(
                f"addons/op-dodatok-{a['code'].lower()}-{y}-mk.md",
                front(
                    f"op-dodatok-{a['code'].lower()}-{y}",
                    f"Додатен интернет пакет {a['gb']} GB ({y})",
                    "mk",
                    y,
                    "addons",
                )
                + f"""# Додаток {a['gb']} GB
## Услови за {y} година

| Ставка | Вредност |
|---|---|
| Шифра | {a['code']} |
| Количина | {a['gb']} GB |
| Важност | {a['days']} дена од активација |
| Цена | **{money(price)} {DEN}** |
| Цена по GB | {money(round(per_gb, 2))} {DEN} |
{prev}
## Правила

Важноста тече од моментот на активација, не од почетокот на пресметковниот период.
Неискористениот сообраќај не се пренесува и не се рефундира.

Пакетот важи само во домашна мрежа. Во роаминг се троши роаминг квота или пакет за
роаминг, не овој додаток.

Редослед на трошење: прво домашната квота од тарифниот пакет, потоа додатоците по
редослед на истекување на важноста.

Може да се активираат повеќе додатоци истовремено. Нема ограничување на бројот.
""",
            )
            w(
                f"addons/op-addon-{a['code'].lower()}-{y}-en.md",
                front(
                    f"op-dodatok-{a['code'].lower()}-{y}",
                    f"Data add-on {a['gb']} GB ({y})",
                    "en",
                    y,
                    "addons",
                )
                + f"""# {a['gb']} GB add-on
## Terms for {y}

| Item | Value |
|---|---|
| Code | {a['code']} |
| Volume | {a['gb']} GB |
| Validity | {a['days']} days from activation |
| Price | **{money(price)} MKD** |
| Price per GB | {money(round(per_gb, 2))} MKD |

## Rules

Validity runs from activation, not from the start of the billing period. Unused data
does not carry over and is not refunded.

The add-on applies in the home network only. While roaming, the roaming allowance or a
roaming pack is used instead.

Consumption order: the tariff plan's domestic allowance first, then add-ons in order of
expiry.

Several add-ons can be active at once. There is no limit on the number.
""",
            )

    zone_by_key = {z.key: z for z in C.ZONES}
    for pk in C.ROAMING_PACKS:
        for y in C.YEARS:
            price = pk["price"][y]
            per_gb = price / pk["gb"]
            z = zone_by_key[pk["zone"]]
            zmk, zen = z.name_mk, z.name_en
            w(
                f"addons/op-roaming-paket-{pk['code'].lower()}-{y}-mk.md",
                front(
                    f"op-roaming-paket-{pk['code'].lower()}-{y}",
                    f"Пакет за роаминг {pk['code']} ({y})",
                    "mk",
                    y,
                    "addons",
                )
                + f"""# Пакет за роаминг {pk['code']}
## Услови за {y} година

| Ставка | Вредност |
|---|---|
| Зона | {zmk} |
| Количина | {pk['gb']} GB |
| Важност | {pk['days']} дена |
| Цена | **{money(price)} {DEN}** |
| Цена по GB | {money(round(per_gb, 2))} {DEN} |

## Правила

Пакетот мора да се активира **пред** почетокот на трошењето. Не се применува наназад
на сообраќај што е веќе наплатен по стандардна тарифа. Ова е најчестата причина за
приговор поврзан со роаминг пакети.

Пакетот важи само во наведената зона. Во друга зона се наплаќа по стандардна тарифа
дури и ако пакетот е активен.

Пакетот не се однесува на зоната на Западен Балкан, каде наплатата е како во домашна
мрежа и пакет не е потребен. Купување пакет за таа зона е непотребен трошок.
""",
            )
            w(
                f"addons/op-roaming-pack-{pk['code'].lower()}-{y}-en.md",
                front(
                    f"op-roaming-paket-{pk['code'].lower()}-{y}",
                    f"Roaming pack {pk['code']} ({y})",
                    "en",
                    y,
                    "addons",
                )
                + f"""# Roaming pack {pk['code']}
## Terms for {y}

| Item | Value |
|---|---|
| Zone | {zen} |
| Volume | {pk['gb']} GB |
| Validity | {pk['days']} days |
| Price | **{money(price)} MKD** |
| Price per GB | {money(round(per_gb, 2))} MKD |

## Rules

The pack must be activated **before** usage begins. It is not applied retrospectively
to traffic already charged at the standard rate. This is the most common ground for a
roaming-pack complaint.

The pack applies only in the stated zone. In another zone the standard tariff applies
even while the pack is active.

The pack does not apply to the Western Balkans zone, where charging is at domestic
rates and no pack is needed. Buying one for that zone is wasted money.
""",
            )

if __name__ == "__main__":
    for fn in (
        gen_price_lists,
        gen_roaming,
        gen_troubleshooting,
        gen_campaigns,
        gen_devices,
        gen_procedures,
        gen_misc,
        gen_rest,
        gen_country_sheets,
        gen_bulletins,
        gen_kb_articles,
        gen_coverage,
        gen_points_programme,
        gen_device_specs,
        gen_full_specs,
        gen_prepaid,
        gen_billing,
        gen_complaints,
        gen_contract_terms,
        gen_addons,
    ):
        fn()

    total_chars = sum(p.read_text(encoding="utf-8").__len__() for p in written)
    mk = [p for p in written if p.stem.endswith("-mk")]
    en = [p for p in written if p.stem.endswith("-en")]
    est = sum(
        len(p.read_text(encoding="utf-8")) / (2.1 if p.stem.endswith("-mk") else 4.1)
        for p in written
    )
    print(f"files      {len(written)}  ({len(mk)} mk, {len(en)} en)")
    print(f"chars      {total_chars:,}")
    print(f"~tokens    {int(est):,}")
    print(f"families   {len({p.parent.name for p in written})}")
