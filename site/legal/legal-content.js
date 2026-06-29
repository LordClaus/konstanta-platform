/* ═══════════════════════════════════════════════════════════════════════════
   KONSTANTA WORK — legal documents content (candidate site #2)

   Operator is a UKRAINIAN sole proprietor (ФОП), licensed by declaration for
   mediation of employment ABROAD. All documents are under the law of UKRAINE.
   Four documents in CZ/UA/EN: Terms of Use, Privacy Policy (ЗУ «Про захист
   персональних даних»), Cookie Policy, Complaints/Appeals channel.

   The two candidate sites belong to the SAME operator — only the M.brand/url
   differ between sites.
═══════════════════════════════════════════════════════════════════════════ */
window.LEGAL = (function () {
    'use strict';

    const M = {
        brand:      'KONSTANTA',
        domain:     'konstanta-agency.cz',
        url:        'https://www.konstanta-agency.cz',
        rnokpp:     '3400101383',
        kved:       '78.10',
        declaration:'162380/26',
        phone:      '+380 98 118 7495',
        email:      'julazejkan777@gmail.com',
        op: {
            ua: 'Фізична особа-підприємець Бокова Юлія Василівна',
            cz: 'Fyzická osoba — podnikatel (FOP) Yuliia Bokova, Ukrajina',
            en: 'Yuliia Bokova — sole proprietor (FOP), Ukraine',
        },
        addr: {
            ua: '88000, Україна, м. Ужгород, вул. Загорська, буд. 51Б, офіс 401',
            cz: '88000, Užhorod, Zahorská 51B, kancelář 401, Ukrajina',
            en: '88000, Uzhhorod, Zahorska St. 51B, office 401, Ukraine',
        },
        updated: { cz: '29. 6. 2026', ua: '29 червня 2026 р.', en: 'June 29, 2026' },
    };

    const docs = {

        /* ───────────────────────────── 1. TERMS OF USE ───────────────────────── */
        podminky: {
            title: { cz: 'Podmínky užití webu', ua: 'Умови користування сайтом', en: 'Terms of Use' },
            body: {
                ua: `
<h2>1. Загальні положення</h2>
<p>Ці умови регулюють користування вебсайтом ${M.url} (далі — «сайт»), власником якого є ${M.op.ua}, РНОКПП ${M.rnokpp}, адреса: ${M.addr.ua} (далі — «оператор»). Користуючись сайтом, ви погоджуєтеся з цими умовами.</p>

<h2>2. Характер послуги</h2>
<p>Оператор здійснює посередництво у працевлаштуванні за кордоном (КВЕД ${M.kved} — діяльність агентств працевлаштування) на підставі декларації про провадження господарської діяльності № ${M.declaration}, відповідно до Закону України «Про зайнятість населення». Оператор є посередником: безпосереднім роботодавцем виступає іноземна компанія. Надсилання анкети не створює трудових відносин між вами та оператором.</p>

<h2>3. Обліковий запис</h2>
<p>Окремі функції (відгук, надсилання анкети) потребують реєстрації. Зазначені дані мають бути правдивими й актуальними. За збереження конфіденційності даних для входу відповідає користувач.</p>

<h2>4. Правила користування</h2>
<ul>
<li>не зазначати неправдиві, неповні або чужі персональні дані;</li>
<li>не розміщувати протиправний, образливий, оманливий чи спам-контент;</li>
<li>не втручатися в роботу сайту й не збирати дані автоматизовано;</li>
<li>використовувати сайт лише за призначенням.</li>
</ul>

<h2>5. Надсилання анкети та резюме</h2>
<p>Надсилаючи форму чи резюме, кандидат підтверджує правдивість даних і надає згоду на їх обробку та передачу потенційним роботодавцям (зокрема за кордон) з метою працевлаштування. Деталі — у <a href="ochrana-udaju.html">Політиці конфіденційності</a>. Послуги для кандидата безкоштовні.</p>

<h2>6. Інтелектуальна власність</h2>
<p>Вміст сайту (тексти, графіка, логотип, структура) належить оператору або його партнерам і охороняється авторським правом. Копіювання чи комерційне використання без згоди заборонено.</p>

<h2>7. Посилання третіх сторін</h2>
<p>Сайт може містити посилання на сторонні ресурси (карти, соцмережі). Оператор не відповідає за їхній вміст і доступність.</p>

<h2>8. Обмеження відповідальності</h2>
<p>Оператор докладає розумних зусиль для точності інформації, але не гарантує її повноти чи безперебійної роботи сайту й не відповідає за шкоду від користування сайтом у межах, дозволених законом.</p>

<h2>9. Зміни умов</h2>
<p>Оператор може змінювати ці умови; нова редакція діє з моменту публікації на сайті.</p>

<h2>10. Застосовне право</h2>
<p>Ці умови регулюються правом України. Спори підлягають розгляду судами України.</p>

<h2>11. Контакти</h2>
<p>${M.op.ua}<br>${M.addr.ua}<br>E-mail: ${M.email} · Тел.: ${M.phone}</p>
<p class="legal-meta">Чинні з ${M.updated.ua}</p>
`,
                cz: `
<h2>1. Úvodní ustanovení</h2>
<p>Tyto podmínky upravují užívání webu ${M.url} (dále jen „web“), jehož vlastníkem je ${M.op.cz}, daňové č. (RNOKPP) ${M.rnokpp}, adresa: ${M.addr.cz} (dále jen „provozovatel“). Užíváním webu vyjadřujete souhlas s těmito podmínkami.</p>

<h2>2. Charakter služby</h2>
<p>Provozovatel zajišťuje zprostředkování zaměstnání v zahraničí (NACE/KVED ${M.kved}) na základě deklarace o provozování hospodářské činnosti č. ${M.declaration} podle ukrajinského zákona „O zaměstnanosti“. Provozovatel je zprostředkovatel — zaměstnavatelem je zahraniční společnost. Odesláním dotazníku nevzniká pracovní poměr s provozovatelem.</p>

<h2>3. Uživatelský účet</h2>
<p>Některé funkce (recenze, odeslání dotazníku) vyžadují registraci. Uvedené údaje musí být pravdivé a aktuální. Za důvěrnost přihlašovacích údajů odpovídá uživatel.</p>

<h2>4. Pravidla používání</h2>
<ul>
<li>neuvádět nepravdivé, neúplné nebo cizí osobní údaje;</li>
<li>nezveřejňovat protiprávní, urážlivý, klamavý nebo spamový obsah;</li>
<li>nezasahovat do provozu webu ani automatizovaně sbírat data;</li>
<li>používat web jen k zamýšlenému účelu.</li>
</ul>

<h2>5. Odeslání dotazníku a životopisu</h2>
<p>Odesláním formuláře či životopisu uchazeč potvrzuje pravdivost údajů a souhlasí s jejich zpracováním a předáním potenciálním zaměstnavatelům (i do zahraničí) za účelem zprostředkování práce. Podrobnosti v <a href="ochrana-udaju.html">Zásadách ochrany osobních údajů</a>. Služby jsou pro uchazeče zdarma.</p>

<h2>6. Duševní vlastnictví</h2>
<p>Obsah webu (texty, grafika, logo, struktura) patří provozovateli či jeho partnerům a je chráněn autorským právem. Kopírování či komerční využití bez souhlasu je zakázáno.</p>

<h2>7. Odkazy třetích stran</h2>
<p>Web může obsahovat odkazy na cizí stránky (mapy, sociální sítě). Provozovatel neodpovídá za jejich obsah ani dostupnost.</p>

<h2>8. Vyloučení odpovědnosti</h2>
<p>Provozovatel usiluje o správnost informací, neručí však za jejich úplnost ani za nepřetržitou dostupnost webu a neodpovídá za škodu z užívání webu v rozsahu povoleném zákonem.</p>

<h2>9. Změny podmínek</h2>
<p>Provozovatel může podmínky měnit; nové znění platí od zveřejnění na webu.</p>

<h2>10. Rozhodné právo</h2>
<p>Tyto podmínky se řídí právem Ukrajiny. Spory řeší soudy Ukrajiny.</p>

<h2>11. Kontakt</h2>
<p>${M.op.cz}<br>${M.addr.cz}<br>E-mail: ${M.email} · Tel.: ${M.phone}</p>
<p class="legal-meta">Účinné od ${M.updated.cz}.</p>
`,
                en: `
<h2>1. Introduction</h2>
<p>These Terms govern the use of the website ${M.url} (the “Website”), owned by ${M.op.en}, tax no. (RNOKPP) ${M.rnokpp}, address: ${M.addr.en} (the “Operator”). By using the Website you agree to these Terms.</p>

<h2>2. Nature of the service</h2>
<p>The Operator provides mediation of employment abroad (NACE/KVED ${M.kved}) under business-activity declaration No. ${M.declaration}, pursuant to Ukraine's Law “On Employment of the Population”. The Operator is an intermediary — the employer is a foreign company. Submitting the form does not create an employment relationship with the Operator.</p>

<h2>3. User account</h2>
<p>Some features (reviews, submitting a form) require registration. The data provided must be true and current. The user is responsible for keeping login credentials confidential.</p>

<h2>4. Rules of use</h2>
<ul>
<li>do not provide false, incomplete or third-party personal data;</li>
<li>do not post unlawful, offensive, misleading or spam content;</li>
<li>do not interfere with the Website or scrape data;</li>
<li>use the Website only as intended.</li>
</ul>

<h2>5. Submitting a form and CV</h2>
<p>By submitting the form or a CV, the candidate confirms the data is true and consents to its processing and transfer to prospective employers (including abroad) for job mediation. Details in the <a href="ochrana-udaju.html">Privacy Policy</a>. Services are free for candidates.</p>

<h2>6. Intellectual property</h2>
<p>The Website content (text, graphics, logo, structure) belongs to the Operator or its partners and is protected by copyright. Copying or commercial use without consent is prohibited.</p>

<h2>7. Third-party links</h2>
<p>The Website may link to third-party sites (maps, social networks). The Operator is not responsible for their content or availability.</p>

<h2>8. Disclaimer</h2>
<p>The Operator strives for accuracy but does not warrant completeness or uninterrupted availability and is not liable for damage from use of the Website to the extent permitted by law.</p>

<h2>9. Changes</h2>
<p>The Operator may amend these Terms; the new version applies from publication on the Website.</p>

<h2>10. Governing law</h2>
<p>These Terms are governed by the law of Ukraine. Disputes are resolved by the courts of Ukraine.</p>

<h2>11. Contact</h2>
<p>${M.op.en}<br>${M.addr.en}<br>Email: ${M.email} · Phone: ${M.phone}</p>
<p class="legal-meta">Effective from ${M.updated.en}.</p>
`,
            },
        },

        /* ─────────────────── 2. PRIVACY POLICY ───────────────────────────────── */
        ochranaUdaju: {
            title: { cz: 'Zásady ochrany osobních údajů', ua: 'Політика конфіденційності', en: 'Privacy Policy' },
            body: {
                ua: `
<p>Ця політика описує, як ${M.op.ua} обробляє персональні дані відповідно до Закону України «Про захист персональних даних» № 2297-VI.</p>

<h2>1. Володілець персональних даних</h2>
<p>${M.op.ua}, РНОКПП ${M.rnokpp}, ${M.addr.ua}. Контакт із питань даних: ${M.email}, тел. ${M.phone}.</p>

<h2>2. Які дані ми обробляємо</h2>
<ul>
<li><strong>Ідентифікаційні та контактні:</strong> ім'я та прізвище, дата народження, e-mail, телефон;</li>
<li><strong>Професійні:</strong> професія, досвід, резюме (CV), бажане місто;</li>
<li><strong>Надісланий вами контент:</strong> текст анкети, відгуки;</li>
<li><strong>Технічні:</strong> IP-адреса, cookies (див. <a href="cookies.html">Політику cookies</a>).</li>
</ul>

<h2>3. Мета та правові підстави</h2>
<ul>
<li><strong>Посередництво у працевлаштуванні</strong> та комунікація з роботодавцями — на підставі вашої згоди та для вчинення дій до/під час надання послуги;</li>
<li><strong>Ведення облікового запису й зв'язок</strong> із кандидатом;</li>
<li><strong>Виконання обов'язків</strong>, передбачених законом.</li>
</ul>
<p>Згоду можна відкликати будь-коли, написавши на ${M.email}.</p>

<h2>4. Кому передаються дані</h2>
<p>Дані можуть передаватися потенційним роботодавцям (зокрема за кордоном) для працевлаштування, а також постачальникам послуг (хостинг, e-mail, IT) як розпорядникам, та органам влади у випадках, передбачених законом.</p>

<h2>5. Транскордонна передача</h2>
<p>Оскільки працевлаштування відбувається за кордоном, ваші дані можуть передаватися іноземним роботодавцям. Ми вживаємо розумних заходів для їх захисту під час такої передачі.</p>

<h2>6. Строк зберігання</h2>
<p>Дані зберігаються протягом часу, потрібного для мети обробки (зазвичай до 3 років від останнього контакту), або довше, якщо цього вимагає закон. Після цього вони видаляються або знеособлюються.</p>

<h2>7. Ваші права</h2>
<p>Ви маєте право знати про обробку, отримати доступ до своїх даних, вимагати їх зміни чи видалення, відкликати згоду та подати скаргу до <strong>Уповноваженого Верховної Ради України з прав людини</strong> (ombudsman.gov.ua). Запити надсилайте на ${M.email}.</p>

<h2>8. Безпека</h2>
<p>Ми застосовуємо розумні технічні та організаційні заходи (шифрування HTTPS, контроль доступу) для захисту даних від несанкціонованого доступу, втрати чи зловживання.</p>

<p class="legal-meta">Чинна з ${M.updated.ua}</p>
`,
                cz: `
<p>Tyto zásady popisují, jak ${M.op.cz} zpracovává osobní údaje podle ukrajinského zákona „O ochraně osobních údajů“ č. 2297-VI.</p>

<h2>1. Správce údajů</h2>
<p>${M.op.cz}, RNOKPP ${M.rnokpp}, ${M.addr.cz}. Kontakt ve věci údajů: ${M.email}, tel. ${M.phone}.</p>

<h2>2. Jaké údaje zpracováváme</h2>
<ul>
<li><strong>Identifikační a kontaktní:</strong> jméno a příjmení, datum narození, e-mail, telefon;</li>
<li><strong>Profesní:</strong> profese, praxe, životopis (CV), preferované místo;</li>
<li><strong>Obsah od vás:</strong> text dotazníku, recenze;</li>
<li><strong>Technické:</strong> IP adresa, cookies (viz <a href="cookies.html">Zásady cookies</a>).</li>
</ul>

<h2>3. Účely a právní základ</h2>
<ul>
<li><strong>Zprostředkování zaměstnání</strong> a komunikace se zaměstnavateli — na základě vašeho souhlasu a pro poskytnutí služby;</li>
<li><strong>Vedení účtu a kontakt</strong> s uchazečem;</li>
<li><strong>Plnění zákonných povinností.</strong></li>
</ul>
<p>Souhlas lze kdykoli odvolat na ${M.email}.</p>

<h2>4. Komu údaje předáváme</h2>
<p>Údaje mohou být předány potenciálním zaměstnavatelům (i v zahraničí) za účelem zaměstnání, dále poskytovatelům služeb (hosting, e-mail, IT) jako zpracovatelům a orgánům veřejné moci v zákonem stanovených případech.</p>

<h2>5. Předávání do zahraničí</h2>
<p>Protože zaměstnání probíhá v zahraničí, vaše údaje mohou být předány zahraničním zaměstnavatelům. Při takovém předání přijímáme přiměřená ochranná opatření.</p>

<h2>6. Doba uchování</h2>
<p>Údaje uchováváme po dobu nezbytnou k účelu (zpravidla do 3 let od posledního kontaktu), případně déle, vyžaduje-li to zákon. Poté je vymažeme nebo anonymizujeme.</p>

<h2>7. Vaše práva</h2>
<p>Máte právo vědět o zpracování, na přístup, opravu či výmaz, odvolání souhlasu a podání stížnosti u <strong>zmocněnce Nejvyšší rady Ukrajiny pro lidská práva</strong> (ombudsman.gov.ua). Žádosti zasílejte na ${M.email}.</p>

<h2>8. Zabezpečení</h2>
<p>Přijímáme přiměřená technická a organizační opatření (šifrování HTTPS, řízení přístupu) na ochranu údajů.</p>

<p class="legal-meta">Účinné od ${M.updated.cz}.</p>
`,
                en: `
<p>This policy describes how ${M.op.en} processes personal data under Ukraine's Law “On Personal Data Protection” No. 2297-VI.</p>

<h2>1. Data controller</h2>
<p>${M.op.en}, RNOKPP ${M.rnokpp}, ${M.addr.en}. Data contact: ${M.email}, phone ${M.phone}.</p>

<h2>2. What data we process</h2>
<ul>
<li><strong>Identification and contact:</strong> name, date of birth, email, phone;</li>
<li><strong>Professional:</strong> profession, experience, CV, preferred location;</li>
<li><strong>Content you send:</strong> form text, reviews;</li>
<li><strong>Technical:</strong> IP address, cookies (see <a href="cookies.html">Cookie Policy</a>).</li>
</ul>

<h2>3. Purposes and legal basis</h2>
<ul>
<li><strong>Employment mediation</strong> and communication with employers — based on your consent and to provide the service;</li>
<li><strong>Account management and contact</strong> with the candidate;</li>
<li><strong>Compliance</strong> with legal obligations.</li>
</ul>
<p>Consent may be withdrawn at any time by writing to ${M.email}.</p>

<h2>4. Who we share data with</h2>
<p>Data may be shared with prospective employers (including abroad) for employment, with service providers (hosting, email, IT) as processors, and with authorities where required by law.</p>

<h2>5. Cross-border transfer</h2>
<p>As employment takes place abroad, your data may be transferred to foreign employers. We take reasonable measures to protect it during such transfers.</p>

<h2>6. Retention</h2>
<p>We keep data for as long as necessary for the purpose (typically up to 3 years from the last contact) or longer if required by law, after which it is deleted or anonymised.</p>

<h2>7. Your rights</h2>
<p>You have the right to be informed, to access, rectify or erase your data, to withdraw consent, and to lodge a complaint with the <strong>Ukrainian Parliament Commissioner for Human Rights</strong> (ombudsman.gov.ua). Send requests to ${M.email}.</p>

<h2>8. Security</h2>
<p>We apply reasonable technical and organisational measures (HTTPS encryption, access control) to protect data.</p>

<p class="legal-meta">Effective from ${M.updated.en}.</p>
`,
            },
        },

        /* ───────────────────────────── 3. COOKIE POLICY ──────────────────────── */
        cookies: {
            title: { cz: 'Zásady používání cookies', ua: 'Політика щодо cookies', en: 'Cookie Policy' },
            body: {
                ua: `
<h2>1. Що таке cookies</h2>
<p>Cookies та подібні технології (наприклад, local storage) — невеликі файли у вашому браузері. Сайт ${M.url} використовує їх для роботи та запам'ятовування ваших налаштувань.</p>

<h2>2. Які cookies ми використовуємо</h2>
<ul>
<li><strong>Необхідні (технічні):</strong> мова, тема, згода на cookies, вхід користувача. Без них сайт працює некоректно.</li>
<li><strong>Функціональні / третіх сторін:</strong> вхід через Google та вбудована карта (Google Maps), які можуть зберігати власні cookies згідно з <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">політикою Google</a>.</li>
</ul>

<h2>3. Згода та відкликання</h2>
<p>Під час першого візиту ми просимо згоду. Її можна відкликати, видаливши cookies у браузері або знову викликавши панель згоди.</p>

<h2>4. Налаштування браузера</h2>
<p>Зберігання cookies можна обмежити чи заборонити в налаштуваннях браузера; це може вплинути на роботу сайту.</p>

<h2>5. Докладніше</h2>
<p>Обробка даних, отриманих через cookies, регулюється <a href="ochrana-udaju.html">Політикою конфіденційності</a>.</p>

<p class="legal-meta">Чинна з ${M.updated.ua}</p>
`,
                cz: `
<h2>1. Co jsou cookies</h2>
<p>Cookies a podobné technologie (např. local storage) jsou malé soubory ve vašem prohlížeči. Web ${M.url} je používá k provozu a zapamatování nastavení.</p>

<h2>2. Jaké cookies používáme</h2>
<ul>
<li><strong>Nezbytné (technické):</strong> jazyk, motiv, souhlas s cookies, přihlášení. Bez nich web nefunguje správně.</li>
<li><strong>Funkční / třetích stran:</strong> přihlášení přes Google a vložená mapa (Google Maps) mohou ukládat vlastní cookies dle <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">zásad Google</a>.</li>
</ul>

<h2>3. Souhlas a odvolání</h2>
<p>Při první návštěvě žádáme o souhlas. Lze jej odvolat smazáním cookies v prohlížeči nebo opětovným vyvoláním lišty souhlasu.</p>

<h2>4. Nastavení prohlížeče</h2>
<p>Ukládání cookies lze omezit či zakázat v prohlížeči; může to ovlivnit funkčnost webu.</p>

<h2>5. Více informací</h2>
<p>Zpracování údajů z cookies se řídí <a href="ochrana-udaju.html">Zásadami ochrany osobních údajů</a>.</p>

<p class="legal-meta">Účinné od ${M.updated.cz}.</p>
`,
                en: `
<h2>1. What cookies are</h2>
<p>Cookies and similar technologies (e.g. local storage) are small files in your browser. The website ${M.url} uses them to operate and remember your settings.</p>

<h2>2. Cookies we use</h2>
<ul>
<li><strong>Necessary (technical):</strong> language, theme, cookie consent, sign-in. The site does not work correctly without them.</li>
<li><strong>Functional / third-party:</strong> Google sign-in and the embedded Google Maps may set their own cookies under <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Google's policy</a>.</li>
</ul>

<h2>3. Consent and withdrawal</h2>
<p>We ask for consent on your first visit. You can withdraw it by deleting cookies in your browser or re-opening the consent bar.</p>

<h2>4. Browser settings</h2>
<p>You can restrict or block cookies in your browser; this may affect the site's functionality.</p>

<h2>5. More information</h2>
<p>Processing of data from cookies is governed by the <a href="ochrana-udaju.html">Privacy Policy</a>.</p>

<p class="legal-meta">Effective from ${M.updated.en}.</p>
`,
            },
        },

        /* ──────────────────────── 4. COMPLAINTS / APPEALS ────────────────────── */
        oznamovatele: {
            title: { cz: 'Kanál pro podněty a stížnosti', ua: 'Канал звернень та скарг', en: 'Complaints & Appeals' },
            body: {
                ua: `
<h2>1. Призначення</h2>
<p>Ми цінуємо зворотний зв'язок. Цей канал дозволяє кандидатам і партнерам подати звернення, скаргу чи повідомлення про можливе порушення в роботі оператора.</p>

<h2>2. Як подати звернення</h2>
<ul>
<li><strong>E-mail:</strong> ${M.email} (тема «Звернення / скарга»);</li>
<li><strong>Телефон:</strong> ${M.phone};</li>
<li><strong>Особисто</strong> за попередньою домовленістю: ${M.addr.ua}.</li>
</ul>
<p>За бажанням звернення можна подати анонімно.</p>

<h2>3. Розгляд</h2>
<p>Ми підтверджуємо отримання та розглядаємо звернення в розумний строк, як правило до 30 днів (відповідно до Закону України «Про звернення громадян»). За потреби строк може бути обґрунтовано продовжено.</p>

<h2>4. Конфіденційність і захист</h2>
<p>Особу заявника ми зберігаємо в конфіденційності та не допускаємо переслідування за добросовісне звернення. Персональні дані в межах звернення обробляються лише для його розгляду згідно з <a href="ochrana-udaju.html">Політикою конфіденційності</a>.</p>

<p class="legal-meta">Чинний з ${M.updated.ua}</p>
`,
                cz: `
<h2>1. Účel</h2>
<p>Vážíme si zpětné vazby. Tento kanál umožňuje uchazečům a partnerům podat podnět, stížnost nebo upozornění na možné porušení v činnosti provozovatele.</p>

<h2>2. Jak podat podnět</h2>
<ul>
<li><strong>E-mail:</strong> ${M.email} (předmět „Podnět / stížnost“);</li>
<li><strong>Telefon:</strong> ${M.phone};</li>
<li><strong>Osobně</strong> po předchozí domluvě: ${M.addr.cz}.</li>
</ul>
<p>Podnět lze podat i anonymně.</p>

<h2>3. Vyřízení</h2>
<p>Přijetí potvrdíme a podnět vyřídíme v přiměřené lhůtě, zpravidla do 30 dnů (dle ukrajinského zákona „O podáních občanů“). V odůvodněných případech lze lhůtu prodloužit.</p>

<h2>4. Důvěrnost a ochrana</h2>
<p>Totožnost podatele držíme v důvěrnosti a nepřipouštíme postih za podnět podaný v dobré víře. Osobní údaje v rámci podnětu zpracováváme jen pro jeho vyřízení dle <a href="ochrana-udaju.html">Zásad ochrany osobních údajů</a>.</p>

<p class="legal-meta">Účinné od ${M.updated.cz}.</p>
`,
                en: `
<h2>1. Purpose</h2>
<p>We value feedback. This channel lets candidates and partners submit a suggestion, complaint or report of a possible breach in the Operator's activity.</p>

<h2>2. How to submit</h2>
<ul>
<li><strong>Email:</strong> ${M.email} (subject “Appeal / complaint”);</li>
<li><strong>Phone:</strong> ${M.phone};</li>
<li><strong>In person</strong> by prior arrangement: ${M.addr.en}.</li>
</ul>
<p>Submissions may be anonymous.</p>

<h2>3. Handling</h2>
<p>We acknowledge receipt and handle submissions within a reasonable time, normally up to 30 days (under Ukraine's Law “On Citizens' Appeals”). The period may be reasonably extended where justified.</p>

<h2>4. Confidentiality and protection</h2>
<p>We keep the submitter's identity confidential and allow no retaliation for a good-faith submission. Personal data within a submission is processed only to handle it, per the <a href="ochrana-udaju.html">Privacy Policy</a>.</p>

<p class="legal-meta">Effective from ${M.updated.en}.</p>
`,
            },
        },
    };

    return { meta: M, docs };
})();
