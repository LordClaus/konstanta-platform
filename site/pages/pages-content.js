/* ═══════════════════════════════════════════════════════════════════════════
   KONSTANTA WORK — content pages (About / How it works / FAQ), CZ/UA/EN.

   Rendered by pages.js into the thin shells pro-nas.html / jak-to-funguje.html /
   faq.html. FAQ is kept as a structured array so the same data renders the
   accordion AND a FAQPage JSON-LD (rich result in Google).

   Same legal entity as site #1 — only the M (meta) block differs between sites.
═══════════════════════════════════════════════════════════════════════════ */
window.PAGES = (function () {
    'use strict';

    const M = {
        brand:   'KONSTANTA',
        op:      'ФОП Бокова Юлія Василівна',
        phone:   '+380 98 118 7495',
        email:   'julazejkan777@gmail.com',
        address: 'м. Ужгород, вул. Загорська 51Б, офіс 401, Україна',
        declaration: '162380/26',
    };

    const pages = {

        /* ───────────────────────────── ABOUT ─────────────────────────────── */
        about: {
            title: { cz: 'O nás', ua: 'Про нас', en: 'About Us' },
            body: {
                cz: `
<p class="lead">${M.brand} je ukrajinská personální agentura se sídlem v Užhorodu, která pomáhá občanům Ukrajiny získat oficiální práci v zahraničí (Česká republika). Zaměřujeme se na pozice ve výrobě, skladech, úklidu a dopravě.</p>

<h2>Naše poslání</h2>
<p>Pomáháme lidem najít stabilní a legální práci v zahraničí — bez prostředníků, bez skrytých poplatků a s plnou podporou na každém kroku, od prvního kontaktu až po nástup do práce.</p>

<h2>Proč právě my</h2>
<ul>
<li><strong>Oficiální zaměstnání</strong> — pracovní smlouva, sociální a zdravotní pojištění dle českého práva.</li>
<li><strong>Pro uchazeče zdarma</strong> — naše služby hradí zaměstnavatel, od kandidátů nevybíráme žádné poplatky.</li>
<li><strong>Podpora ve vašem jazyce</strong> — komunikujeme ukrajinsky, česky i anglicky.</li>
<li><strong>Ubytování</strong> — u řady pozic zajišťujeme nebo pomáháme najít bydlení.</li>
<li><strong>Transparentnost</strong> — předem znáte mzdu, místo i podmínky.</li>
</ul>

<h2>Důvěra a legálnost</h2>
<p>Činnost vykonává ${M.op} (KVED 78.10) na základě deklarace o provozování hospodářské činnosti — zprostředkování zaměstnání v zahraničí č. ${M.declaration}. Osobní údaje zpracováváme dle ukrajinského zákona „O ochraně osobních údajů“.</p>

<p>Máte dotaz? Napište na <a href="mailto:${M.email}">${M.email}</a> nebo zavolejte na ${M.phone}.</p>
`,
                ua: `
<p class="lead">${M.brand} — українська кадрова агенція з офісом в Ужгороді, що допомагає громадянам України офіційно працевлаштуватися за кордоном (Чехія). Спеціалізуємось на вакансіях у сферах виробництва, складів, прибирання та водіїв.</p>

<h2>Наша місія</h2>
<p>Допомагаємо людям знайти стабільну та легальну роботу за кордоном — без посередників, без прихованих платежів і з повною підтримкою на кожному кроці: від першого контакту до виходу на роботу.</p>

<h2>Чому саме ми</h2>
<ul>
<li><strong>Офіційне працевлаштування</strong> — трудовий договір, соціальне й медичне страхування за чеським законом.</li>
<li><strong>Безкоштовно для кандидата</strong> — наші послуги оплачує роботодавець, з кандидатів ми не беремо плати.</li>
<li><strong>Підтримка вашою мовою</strong> — спілкуємось українською, чеською та англійською.</li>
<li><strong>Житло</strong> — для багатьох вакансій забезпечуємо або допомагаємо знайти житло.</li>
<li><strong>Прозорість</strong> — ви заздалегідь знаєте зарплату, місто та умови.</li>
</ul>

<h2>Довіра та легальність</h2>
<p>Діяльність провадить ${M.op} (КВЕД 78.10) на підставі декларації про провадження господарської діяльності з посередництва у працевлаштуванні за кордоном № ${M.declaration}. Обробка персональних даних — згідно із Законом України «Про захист персональних даних».</p>

<p>Маєте питання? Напишіть на <a href="mailto:${M.email}">${M.email}</a> або зателефонуйте ${M.phone}.</p>
`,
                en: `
<p class="lead">${M.brand} is a Ukrainian recruitment agency based in Uzhhorod that helps Ukrainian citizens find official work abroad (Czech Republic). We specialise in positions in manufacturing, warehousing, cleaning and driving.</p>

<h2>Our mission</h2>
<p>We help people find stable, legal work abroad — no middlemen, no hidden fees, and full support at every step, from the first contact to your first day at work.</p>

<h2>Why choose us</h2>
<ul>
<li><strong>Official employment</strong> — an employment contract with social and health insurance under Czech law.</li>
<li><strong>Free for candidates</strong> — our services are paid by the employer; we never charge job seekers.</li>
<li><strong>Support in your language</strong> — we speak Ukrainian, Czech and English.</li>
<li><strong>Accommodation</strong> — for many positions we arrange or help find housing.</li>
<li><strong>Transparency</strong> — you know the salary, location and conditions up front.</li>
</ul>

<h2>Trust and legality</h2>
<p>The activity is carried out by ${M.op} (KVED 78.10) under business-activity declaration No. ${M.declaration} for mediation of employment abroad. Personal data is processed under Ukraine's Law “On Personal Data Protection”.</p>

<p>Have a question? Email <a href="mailto:${M.email}">${M.email}</a> or call ${M.phone}.</p>
`,
            },
        },

        /* ──────────────────────── HOW IT WORKS ────────────────────────────── */
        how: {
            title: { cz: 'Jak to funguje', ua: 'Як це працює', en: 'How It Works' },
            body: {
                cz: `
<p class="lead">Cesta od přihlášky k práci v pěti jednoduchých krocích.</p>
<ol class="steps">
<li><strong>Podáte přihlášku.</strong> Vyberte vhodnou pozici a vyplňte krátký dotazník na webu nebo přes Telegram. Můžete přiložit životopis.</li>
<li><strong>Ozveme se vám.</strong> Náš konzultant vás kontaktuje, upřesní detaily a zodpoví dotazy ve vašem jazyce.</li>
<li><strong>Vybereme nabídku.</strong> Najdeme pozici podle vašich preferencí — mzda, lokalita, ubytování.</li>
<li><strong>Připravíme dokumenty.</strong> Pomůžeme se smlouvou a vším potřebným pro legální nástup.</li>
<li><strong>Nástup do práce.</strong> Pomůžeme s příjezdem a ubytováním a zůstáváme v kontaktu i po nástupu.</li>
</ol>
<p>Celý proces je pro uchazeče <strong>zdarma</strong>. <a href="../index.html#apply">Podat přihlášku →</a></p>
`,
                ua: `
<p class="lead">Шлях від заявки до роботи у п'ять простих кроків.</p>
<ol class="steps">
<li><strong>Подаєте заявку.</strong> Оберіть відповідну вакансію та заповніть коротку анкету на сайті або через Telegram. Можна додати резюме.</li>
<li><strong>Ми зв'язуємось із вами.</strong> Наш консультант зателефонує, уточнить деталі та відповість на питання вашою мовою.</li>
<li><strong>Підбираємо пропозицію.</strong> Знаходимо вакансію за вашими побажаннями — зарплата, місто, житло.</li>
<li><strong>Готуємо документи.</strong> Допомагаємо з договором і всім потрібним для легального виходу на роботу.</li>
<li><strong>Вихід на роботу.</strong> Допомагаємо з приїздом і житлом та лишаємось на зв'язку після працевлаштування.</li>
</ol>
<p>Увесь процес для кандидата <strong>безкоштовний</strong>. <a href="../index.html#apply">Подати заявку →</a></p>
`,
                en: `
<p class="lead">From application to work in five simple steps.</p>
<ol class="steps">
<li><strong>You apply.</strong> Pick a suitable position and fill in a short form on the website or via Telegram. You can attach a CV.</li>
<li><strong>We get in touch.</strong> Our consultant contacts you, clarifies the details and answers your questions in your language.</li>
<li><strong>We match an offer.</strong> We find a position based on your preferences — salary, location, housing.</li>
<li><strong>We prepare the paperwork.</strong> We help with the contract and everything needed for a legal start.</li>
<li><strong>You start working.</strong> We help with arrival and accommodation and stay in touch after you start.</li>
</ol>
<p>The whole process is <strong>free</strong> for candidates. <a href="../index.html#apply">Submit an application →</a></p>
`,
            },
        },

        /* ───────────────────────────── FAQ ───────────────────────────────── */
        faq: {
            title: { cz: 'Časté dotazy', ua: 'Часті запитання', en: 'FAQ' },
            items: {
                cz: [
                    { q: 'Jsou vaše služby pro uchazeče placené?', a: 'Ne. Naše služby hradí zaměstnavatel. Od kandidátů nevybíráme žádné poplatky — to je v souladu s českým právem.' },
                    { q: 'Je to oficiální zaměstnání?', a: 'Ano. Pracujete na základě pracovní smlouvy se sociálním a zdravotním pojištěním podle českých zákonů.' },
                    { q: 'Pomáháte s ubytováním?', a: 'U mnoha pozic ano. Zda je ubytování zajištěno, je uvedeno přímo u dané vakance.' },
                    { q: 'Jakou mzdu mohu očekávat a kdy je výplata?', a: 'Mzda je uvedena u každé pozice. Výplata je zpravidla měsíční, dle podmínek konkrétního zaměstnavatele.' },
                    { q: 'Musím umět česky?', a: 'U řady dělnických pozic znalost češtiny není podmínkou. Komunikujeme s vámi ukrajinsky, česky i anglicky.' },
                    { q: 'Jaké dokumenty budu potřebovat?', a: 'Zpravidla cestovní pas a doklady k pobytu/práci v ČR. Konkrétní seznam vám sdělí náš konzultant a pomůže s přípravou.' },
                    { q: 'Mohu se přihlásit bez praxe?', a: 'Ano, máme i pozice bez požadavku na předchozí zkušenosti. Zaškolení probíhá na místě.' },
                    { q: 'Jak dlouho trvá vyřízení?', a: 'Závisí na pozici a dokumentech. Po podání přihlášky se vám ozveme co nejdříve a termíny upřesníme.' },
                    { q: 'Jak podám přihlášku?', a: 'Vyplňte formulář na webu nebo nám napište na Telegramu. Stačí jméno, telefon a profese, životopis je výhodou.' },
                    { q: 'Jak vás mohu kontaktovat?', a: `Napište na ${M.email} nebo zavolejte na ${M.phone}.` },
                ],
                ua: [
                    { q: 'Чи платні ваші послуги для кандидата?', a: 'Ні. Наші послуги оплачує роботодавець. З кандидатів ми не беремо жодної плати — це відповідає чеському законодавству.' },
                    { q: 'Це офіційне працевлаштування?', a: 'Так. Ви працюєте за трудовим договором із соціальним і медичним страхуванням згідно з чеськими законами.' },
                    { q: 'Чи допомагаєте з житлом?', a: 'Для багатьох вакансій — так. Наявність житла вказана безпосередньо біля кожної вакансії.' },
                    { q: 'Яку зарплату очікувати та коли виплати?', a: 'Зарплата вказана біля кожної вакансії. Виплата зазвичай щомісячна, відповідно до умов конкретного роботодавця.' },
                    { q: 'Чи потрібно знати чеську?', a: 'Для багатьох робітничих позицій знання чеської не обов’язкове. Ми спілкуємось українською, чеською та англійською.' },
                    { q: 'Які документи знадобляться?', a: 'Зазвичай закордонний паспорт і документи для перебування/роботи в ЧР. Точний перелік повідомить наш консультант і допоможе з підготовкою.' },
                    { q: 'Чи можна подати заявку без досвіду?', a: 'Так, є вакансії без вимоги попереднього досвіду. Навчання відбувається на місці.' },
                    { q: 'Скільки триває оформлення?', a: 'Залежить від вакансії та документів. Після подання заявки ми зв’яжемось якнайшвидше й уточнимо терміни.' },
                    { q: 'Як подати заявку?', a: 'Заповніть форму на сайті або напишіть нам у Telegram. Достатньо імені, телефону та професії, резюме буде перевагою.' },
                    { q: 'Як з вами зв’язатися?', a: `Напишіть на ${M.email} або зателефонуйте ${M.phone}.` },
                ],
                en: [
                    { q: 'Are your services paid for candidates?', a: 'No. Our services are paid by the employer. We never charge job seekers — this is in line with Czech law.' },
                    { q: 'Is this official employment?', a: 'Yes. You work under an employment contract with social and health insurance under Czech law.' },
                    { q: 'Do you help with accommodation?', a: 'For many positions, yes. Whether housing is provided is shown next to each vacancy.' },
                    { q: 'What salary can I expect and when is payday?', a: 'The salary is listed with each position. Pay is usually monthly, according to the specific employer’s terms.' },
                    { q: 'Do I need to speak Czech?', a: 'For many manual roles Czech is not required. We communicate with you in Ukrainian, Czech and English.' },
                    { q: 'What documents will I need?', a: 'Usually a passport and residence/work documents for the Czech Republic. Our consultant will give you the exact list and help you prepare.' },
                    { q: 'Can I apply without experience?', a: 'Yes, we also have positions with no prior experience required. Training is provided on site.' },
                    { q: 'How long does it take?', a: 'It depends on the position and documents. After you apply we contact you as soon as possible and confirm the timeline.' },
                    { q: 'How do I apply?', a: 'Fill in the form on the website or message us on Telegram. Just your name, phone and profession; a CV is a plus.' },
                    { q: 'How can I contact you?', a: `Email ${M.email} or call ${M.phone}.` },
                ],
            },
        },
    };

    return { meta: M, pages };
})();
