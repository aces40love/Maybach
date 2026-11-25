"""Local browser checks. Quote delivery is mocked; no messages are sent."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urlparse
import json
import mimetypes
import os
import re
import unittest

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ['UNISON_TEST_ARTIFACTS']) if os.environ.get('UNISON_TEST_ARTIFACTS') else None
AXE = os.environ.get('UNISON_AXE_PATH')


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class WebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()
        if ARTIFACTS:
            ARTIFACTS.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        self.context.route('**/*', lambda route: route.continue_() if urlparse(route.request.url).hostname == '127.0.0.1' else route.abort())
        self.page = self.context.new_page()
        self.errors = []
        self.failed_assets = []
        self.quote_requests = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('response', lambda response: self.failed_assets.append(response.url) if response.status >= 400 else None)
        self.page.on('request', lambda request: self.quote_requests.append(request) if request.method == 'POST' else None)
        self.page.goto(self.url, wait_until='networkidle')
        expect(self.page.locator('#preview-note')).to_be_visible()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], 'Browser JavaScript errors')
        self.assertEqual(self.failed_assets, [], 'Missing local assets')

    def fill_request(self, page=None):
        page = page or self.page
        page.locator('#name').fill('Sample Guest')
        page.locator('#phone').fill('6155550100')
        page.locator('#email').fill('guest@example.com')
        page.locator('#date').fill('2030-01-07')
        page.locator('#time').fill('18:30')
        page.locator('#pickup').fill('Nashville hotel')
        page.locator('#destination').fill('The Ryman')
        page.locator('#message').fill('Dinner and a concert. This is a local automated test.')

    def test_01_structure_images_and_internal_links(self):
        expect(self.page.locator('h1')).to_have_text('Arrivedifferently.')
        self.assertEqual(self.page.locator('h1').count(), 1)
        for section in ['sprinter', 'occasions', 'plan', 'details', 'inquire']:
            self.page.locator(f'#{section}').scroll_into_view_if_needed()
            expect(self.page.locator(f'#{section}')).to_be_visible()
        self.page.wait_for_function("Array.from(document.querySelectorAll('main img')).every(i => i.complete && i.naturalWidth > 0)")
        self.assertEqual(self.page.evaluate("Array.from(document.querySelectorAll('img')).filter(i => !i.hasAttribute('alt')).length"), 0)
        missing = self.page.evaluate("""() => Array.from(document.querySelectorAll('a[href^="#"]')).map(a => a.getAttribute('href').slice(1)).filter(id => !document.getElementById(id))""")
        self.assertEqual(missing, [])
        duplicate_ids = self.page.evaluate("""() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id); return ids.filter((id, index) => ids.indexOf(id) !== index); }""")
        self.assertEqual(duplicate_ids, [])
        self.assertEqual(self.page.locator('a[href="tel:+16292595327"]').count(), 5)
        self.assertEqual(self.page.evaluate('localStorage.length'), 0)

    def test_02_gallery_and_hero(self):
        self.page.get_by_role('button', name='Show exterior photograph', exact=True).click()
        expect(self.page.locator('#hero-image')).to_have_attribute('src', 'assets/van-exterior.webp')
        expect(self.page.get_by_role('button', name='Show exterior photograph', exact=True)).to_have_attribute('aria-pressed', 'true')
        self.page.get_by_role('button', name='Open gallery of the Unison Sprinter').click()
        expect(self.page.locator('#gallery-dialog')).to_be_visible()
        expect(self.page.locator('#gallery-count')).to_have_text('02 / 07')
        self.page.keyboard.press('ArrowRight')
        expect(self.page.locator('#gallery-count')).to_have_text('03 / 07')
        expect(self.page.locator('#gallery-image')).to_have_attribute('src', 'assets/leather-detail.webp')
        self.page.get_by_role('button', name='Previous photograph').click()
        expect(self.page.locator('#gallery-count')).to_have_text('02 / 07')
        for _ in range(9):
            self.page.keyboard.press('Tab')
            self.assertTrue(self.page.evaluate("document.querySelector('#gallery-dialog').contains(document.activeElement)"))
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#gallery-dialog')).not_to_be_visible()
        expect(self.page.get_by_role('button', name='Open gallery of the Unison Sprinter')).to_be_focused()

    def test_03_all_pricing_removed_from_site_and_client_code(self):
        self.page.evaluate("document.querySelectorAll('details').forEach(e => e.open = true)")
        text = self.page.locator('body').text_content()
        self.assertIsNone(re.search(r'\$\s*\d|\b\d+(?:\.\d+)?\s*%', text))
        self.assertNotRegex(text.lower(), r'\bestimator\b|\bcalculator\b|\bgratuity\b|\bsurcharge\b')
        self.assertEqual(self.page.locator('input[type="range"], #attach-estimate, #estimate-total').count(), 0)
        self.assertFalse((ROOT / 'pricing.mjs').exists())
        self.assertFalse((ROOT / 'tests' / 'pricing.test.mjs').exists())
        for filename in ['index.html', 'privacy.html', 'app.js', 'analytics.js', 'styles.css']:
            content = (ROOT / filename).read_text()
            self.assertNotRegex(content, r'\$\s*\d|calculateEstimate|fuelPer110Miles|peakPct|vanShortDay|pricing\.mjs')
        expect(self.page.locator('#plan')).to_contain_text('For availability and pricing, please inquire.')
        self.page.locator('#plan-inquiry-link').click()
        expect(self.page.locator('#name')).to_be_focused()

    def test_04_occasion_and_booking_accordions(self):
        self.page.locator('details.occasion').nth(1).locator('summary').click()
        expect(self.page.locator('details.occasion').nth(1)).to_have_attribute('open', '')
        expect(self.page.locator('details.occasion').nth(0)).not_to_have_attribute('open', '')
        self.page.get_by_role('button', name='Plan the big day').click()
        expect(self.page.locator('#occasion')).to_have_value('Wedding')
        self.page.locator('details.occasion').nth(4).locator('summary').click()
        self.page.get_by_role('button', name='Arrange a transfer').click()
        expect(self.page.locator('#occasion')).to_have_value('Airport transfer')
        self.page.locator('.booking-details details').nth(0).locator('summary').click()
        expect(self.page.locator('.booking-details details').nth(0)).to_contain_text('personalized quote')
        self.page.locator('.booking-details details').nth(1).locator('summary').click()
        expect(self.page.locator('.booking-details details').nth(1)).to_contain_text('before you book')

    def test_05_local_request_validation_and_safe_preview(self):
        self.page.locator('#submit-inquiry').click()
        expect(self.page.locator('#request-dialog')).not_to_be_visible()
        self.fill_request()
        self.page.locator('#phone').fill('invalid')
        self.page.locator('#submit-inquiry').click()
        expect(self.page.locator('#request-dialog')).not_to_be_visible()
        self.assertIn('phone number', self.page.locator('#phone').evaluate('(el) => el.validationMessage'))
        self.page.locator('#phone').fill('6155550100')
        self.page.locator('#name').fill('<img src=x onerror=alert(1)>')
        self.page.locator('#submit-inquiry').click()
        expect(self.page.locator('#request-dialog')).to_be_visible()
        expect(self.page.locator('#request-summary')).to_contain_text('<img src=x onerror=alert(1)>')
        expect(self.page.locator('#request-summary')).to_contain_text('provide a personalized quote')
        self.assertEqual(self.page.locator('#request-summary img').count(), 0)
        expect(self.page.locator('#request-dialog')).to_contain_text('Nothing has been sent')
        self.assertTrue(self.page.locator('#email-request').get_attribute('href').startswith('mailto:Info@unisontransportation.com?'))
        self.assertEqual(len(self.quote_requests), 0)
        self.assertEqual(self.page.evaluate('localStorage.length'), 0)
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#name')).to_have_value('<img src=x onerror=alert(1)>')

    def test_06_copy_request_control_with_isolated_clipboard(self):
        self.page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async text => {window.testCopiedText = text}}})")
        self.fill_request()
        self.page.locator('#submit-inquiry').click()
        self.page.locator('#copy-request').click()
        expect(self.page.locator('#copy-status')).to_contain_text('Request copied')
        self.assertIn('Sample Guest', self.page.evaluate('window.testCopiedText'))
        self.assertEqual(len(self.quote_requests), 0)

    def test_07_responsive_layout_and_mobile_menu(self):
        for width in [320, 375, 390, 430, 768, 1024, 1440, 1920]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.page.goto(self.url, wait_until='networkidle')
            overflow = self.page.evaluate('document.documentElement.scrollWidth - window.innerWidth')
            self.assertLessEqual(overflow, 1, f'Horizontal overflow at {width}px')
            hero = self.page.locator('#hero-title').bounding_box()
            self.assertGreaterEqual(hero['x'], 0)
            self.assertLessEqual(hero['x'] + hero['width'], width + 1)
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.goto(self.url, wait_until='networkidle')
        self.page.get_by_role('button', name='Open navigation menu').click()
        expect(self.page.locator('#menu-dialog')).to_be_visible()
        for _ in range(12):
            self.page.keyboard.press('Tab')
            self.assertTrue(self.page.evaluate("document.querySelector('#menu-dialog').contains(document.activeElement)"))
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#menu-dialog')).not_to_be_visible()
        self.page.get_by_role('button', name='Open navigation menu').click()
        self.page.locator('#menu-dialog a[href="#plan"]').click()
        expect(self.page.locator('#menu-dialog')).not_to_be_visible()
        self.assertTrue(self.page.url.endswith('#plan'))
        self.page.locator('#plan-inquiry-link').click()
        expect(self.page.locator('#name')).to_be_focused()

    def test_08_no_script_contact_fallback(self):
        context = self.browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(self.url)
        expect(page.locator('.noscript-notice')).to_be_visible()
        expect(page.locator('.inquiry-form')).not_to_be_visible()
        expect(page.get_by_role('heading', name='Arrive differently.')).to_be_visible()
        expect(page.get_by_role('link', name='Request a personalized quote')).to_be_visible()
        self.assertGreater(page.locator('a[href="tel:+16292595327"]').count(), 0)
        context.close()

    def test_09_mocked_production_inquiry_and_error_recovery(self):
        context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        requests = []
        responses = [
            {'status': 503, 'body': {'error': 'Service temporarily unavailable.'}},
            {'status': 200, 'body': '<p>Fallback page</p>', 'content_type': 'text/html'},
            {'status': 200, 'body': '{invalid json'},
            {'status': 200, 'body': {'error': 'Request rejected.'}},
            {'status': 200, 'body': {}},
            {'status': 200, 'body': {'ok': True}},
        ]
        def mock(route):
            request = route.request
            url = urlparse(request.url)
            if url.hostname != 'unisontransportation.com':
                route.abort()
                return
            if url.path == '/_vercel/insights/script.js':
                route.fulfill(status=200, content_type='application/javascript', body='/* Analytics isolated in local testing. */')
                return
            if url.path == '/api/quote':
                requests.append(request.post_data_json)
                answer = responses.pop(0)
                route.fulfill(status=answer['status'], content_type=answer.get('content_type', 'application/json'), body=answer['body'] if isinstance(answer['body'], str) else json.dumps(answer['body']))
                return
            path = (ROOT / unquote(url.path).lstrip('/')).resolve() if url.path != '/' else ROOT / 'index.html'
            if ROOT not in path.parents or not path.is_file():
                route.fulfill(status=404, body='Not found')
                return
            route.fulfill(path=str(path), content_type=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        context.route('**/*', mock)
        page = context.new_page()
        page.goto('https://unisontransportation.com/', wait_until='networkidle')
        expect(page.locator('#preview-note')).not_to_be_visible()
        self.fill_request(page)
        page.locator('#submit-inquiry').click()
        expect(page.locator('#form-status')).to_contain_text('Service temporarily unavailable.')
        expect(page.locator('#name')).to_have_value('Sample Guest')
        expect(page.locator('#submit-inquiry')).to_be_enabled()
        for message in ['Delivery could not be confirmed.', 'Delivery could not be confirmed.', 'Request rejected.', 'Delivery could not be confirmed.']:
            page.locator('#submit-inquiry').click()
            expect(page.locator('#form-status')).to_contain_text(message)
            expect(page.locator('#submit-inquiry')).to_be_enabled()
            self.assertNotIn('Your request has been received.', page.locator('#form-status').inner_text())
        page.evaluate("document.querySelector('#inquiry-form').requestSubmit(); document.querySelector('#inquiry-form').requestSubmit();")
        expect(page.locator('#form-status')).to_contain_text('Your request has been received.')
        expect(page.locator('#submit-inquiry')).to_be_disabled()
        self.assertEqual(len(requests), 6)
        self.assertEqual(requests[-1]['name'], 'Sample Guest')
        self.assertNotIn('estimate', requests[-1])
        self.assertNotIn('total', requests[-1])
        self.assertEqual(requests[-1]['company_website'], '')
        self.assertEqual(page.evaluate('localStorage.length'), 0)
        page.get_by_role('button', name='Start a new request').click()
        expect(page.locator('#name')).to_have_value('')
        expect(page.locator('#submit-inquiry')).to_be_enabled()
        context.close()

    @unittest.skipUnless(AXE, 'Set UNISON_AXE_PATH to the locally downloaded axe-core script')
    def test_10_automated_accessibility(self):
        for viewport in [{'width': 320, 'height': 900}, {'width': 375, 'height': 900}, {'width': 390, 'height': 844}, {'width': 1440, 'height': 1000}]:
            self.page.set_viewport_size(viewport)
            self.page.goto(self.url, wait_until='networkidle')
            self.page.add_script_tag(path=AXE)
            result = self.page.evaluate("""async () => { const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}); return r.violations.map(v => ({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n => ({target:n.target,summary:n.failureSummary}))})); }""")
            if ARTIFACTS:
                (ARTIFACTS / f'accessibility-{viewport["width"]}.json').write_text(json.dumps(result, indent=2))
            self.assertEqual(result, [], json.dumps(result, indent=2))

    def test_11_privacy_and_screenshots(self):
        self.page.goto(self.url + 'privacy.html', wait_until='networkidle')
        expect(self.page.locator('h1')).to_have_text('Privacy Policy')
        expect(self.page.locator('main')).to_contain_text('Last updated November 25, 2026')
        expect(self.page.locator('main')).to_contain_text('we don’t sell them')
        self.assertNotIn('trip estimate', self.page.locator('main').text_content())
        if ARTIFACTS:
            self.page.goto(self.url, wait_until='networkidle')
            self.page.evaluate('document.fonts.ready')
            self.page.screenshot(path=str(ARTIFACTS / 'desktop-home.png'))
            self.page.screenshot(path=str(ARTIFACTS / 'desktop-full.png'), full_page=True)
            self.page.locator('#plan').screenshot(path=str(ARTIFACTS / 'desktop-concierge.png'), style='.site-header,.skip-link{visibility:hidden!important}')
            self.page.set_viewport_size({'width': 390, 'height': 844})
            self.page.goto(self.url, wait_until='networkidle')
            self.page.screenshot(path=str(ARTIFACTS / 'mobile-home.png'))
            self.page.screenshot(path=str(ARTIFACTS / 'mobile-full.png'), full_page=True)
            self.page.locator('#plan').screenshot(path=str(ARTIFACTS / 'mobile-concierge.png'), style='.site-header,.skip-link{visibility:hidden!important}')

    def test_12_standalone_file_preview(self):
        context = self.browser.new_context(reduced_motion='reduce')
        context.route('https://**/*', lambda route: route.abort())
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((ROOT / 'index.html').as_uri(), wait_until='networkidle')
        expect(page.locator('#preview-note')).to_be_visible()
        page.get_by_role('button', name='Show exterior photograph', exact=True).click()
        expect(page.locator('#hero-image')).to_have_attribute('src', 'assets/van-exterior.webp')
        self.fill_request(page)
        page.locator('#submit-inquiry').click()
        expect(page.locator('#request-dialog')).to_be_visible()
        expect(page.locator('#request-dialog')).to_contain_text('Nothing has been sent')
        self.assertEqual(errors, [])
        context.close()

    def test_13_script_failure_cannot_submit_any_request(self):
        context = self.browser.new_context()
        posts = []
        def prevent_post(route):
            if route.request.method == 'POST':
                posts.append(route.request.url)
                route.fulfill(status=200, body='Intercepted by local test')
            else:
                route.continue_()
        context.route('**/*', prevent_post)
        context.route('**/app.js', lambda route: route.abort())
        page = context.new_page()
        page.goto(self.url, wait_until='networkidle')
        self.fill_request(page)
        expect(page.locator('#submit-inquiry')).to_be_disabled()
        self.assertEqual(page.locator('#inquiry-form').get_attribute('method'), 'dialog')
        page.locator('#email').press('Enter')
        page.evaluate("document.querySelector('#inquiry-form').requestSubmit()")
        page.wait_for_load_state('networkidle')
        self.assertEqual(posts, [])
        self.assertEqual(page.url, self.url)
        context.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
