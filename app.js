const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const previewMode = location.hostname !== 'unisontransportation.com';
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let sending = false;
let requestReceived = false;

const photographs = [
  { src: 'assets/cabin-lounge.webp', alt: 'Quilted rear lounge with starlit ceiling, entertainment screen, and refreshment console', caption: 'The private rear lounge. Settle in and make yourself at home.', width: 1920, height: 1440 },
  { src: 'assets/van-exterior.webp', alt: 'Front three-quarter view of Unison’s black luxury Sprinter', caption: 'The Maybach Sprinter. One vehicle, reserved for your group.', width: 1600, height: 1200 },
  { src: 'assets/leather-detail.webp', alt: 'Diamond-quilted leather seat with Maybach embroidery', caption: 'Diamond-quilted leather. A closer look at the details.', width: 960, height: 1280 },
  { src: 'assets/nashville-arrival.webp', alt: 'Rear of the black Sprinter with the Nashville skyline', caption: 'Right at home in Nashville. Your own way through the city.', width: 1168, height: 1751 },
  { src: 'assets/van-stadium.webp', alt: 'Black Sprinter outside Nissan Stadium in Nashville', caption: 'Nissan Stadium, Nashville. Your ride to the occasion.', width: 1169, height: 865 },
  { src: 'assets/nashville-rear.webp', alt: 'Open rear doors of the Sprinter with Nashville’s skyline behind', caption: 'The rear of the Sprinter, with Nashville just beyond.', width: 1169, height: 778 },
  { src: 'assets/van-front.webp', alt: 'Front view of the black Sprinter and its chrome grille', caption: 'A different arrival, from the very first impression.', width: 960, height: 1280 },
];
const heroSlides = [
  { photo: 0, eyebrow: 'YOUR PRIVATE LOUNGE', title: ['The best seat', 'is already yours.'], caption: 'THE MAYBACH SPRINTER', position: '53% 50%' },
  { photo: 1, eyebrow: 'ONE VAN. JUST YOUR PEOPLE.', title: ['Your plans.', 'Your own way there.'], caption: 'PRIVATE CHAUFFEURED TRANSPORTATION', position: '48% 50%' },
  { photo: 3, eyebrow: 'NASHVILLE & BEYOND', title: ['Make yourself', 'at home here.'], caption: 'BASED IN NASHVILLE, TENNESSEE', position: '50% 43%' },
];
let galleryIndex = 0;

function setImage(image, photograph) {
  image.src = photograph.src;
  image.alt = photograph.alt;
  image.width = photograph.width;
  image.height = photograph.height;
}

$$('[data-hero]').forEach((button) => {
  button.addEventListener('click', () => {
    const slide = heroSlides[Number(button.dataset.hero)];
    const image = $('#hero-image');
    setImage(image, photographs[slide.photo]);
    image.style.objectPosition = slide.position;
    image.classList.remove('photo-changed');
    requestAnimationFrame(() => image.classList.add('photo-changed'));
    $('#hero-photo-eyebrow').textContent = slide.eyebrow;
    $('#hero-photo-title').replaceChildren(document.createTextNode(slide.title[0]), document.createElement('br'), document.createTextNode(slide.title[1]));
    $('#hero-photo-caption').textContent = slide.caption;
    $('.image-explore').dataset.gallery = String(slide.photo);
    $$('[data-hero]').forEach((item) => {
      const active = item === button;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-pressed', String(active));
    });
  });
});

function renderGallery(index) {
  galleryIndex = (index + photographs.length) % photographs.length;
  setImage($('#gallery-image'), photographs[galleryIndex]);
  $('#gallery-caption').textContent = photographs[galleryIndex].caption;
  $('#gallery-count').textContent = `${String(galleryIndex + 1).padStart(2, '0')} / ${String(photographs.length).padStart(2, '0')}`;
}

$$('[data-gallery]').forEach((button) => button.addEventListener('click', () => {
  renderGallery(Number(button.dataset.gallery));
  $('#gallery-dialog').showModal();
}));
$('#gallery-previous').addEventListener('click', () => renderGallery(galleryIndex - 1));
$('#gallery-next').addEventListener('click', () => renderGallery(galleryIndex + 1));
$('#gallery-dialog').addEventListener('keydown', (event) => {
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    event.preventDefault();
    renderGallery(galleryIndex + (event.key === 'ArrowRight' ? 1 : -1));
  }
});
$('.menu-toggle').addEventListener('click', () => $('#menu-dialog').showModal());
$$('#menu-dialog nav a').forEach((link) => link.addEventListener('click', () => $('#menu-dialog').close()));
$$('[data-close]').forEach((button) => button.addEventListener('click', () => document.getElementById(button.dataset.close).close()));
$$('dialog').forEach((dialog) => {
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]')]
      .filter((element) => element.tabIndex >= 0 && element.getClientRects().length);
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
});

function moveToInquiry() {
  $('#inquire').scrollIntoView({ behavior: reducedMotion.matches ? 'instant' : 'smooth', block: 'start' });
  $('#name').focus({ preventScroll: true });
}
$('#plan-inquiry-link').addEventListener('click', (event) => {
  event.preventDefault();
  moveToInquiry();
});
$$('[data-occasion]').forEach((button) => button.addEventListener('click', () => {
  $('#occasion').value = button.dataset.occasion;
  moveToInquiry();
}));

function requestText(payload) {
  const lines = [
    'Unison Transportation trip inquiry', '',
    `Name: ${payload.name}`, `Phone: ${payload.phone}`, `Email: ${payload.email}`,
    `Occasion: ${payload.occasion}`, `Guests: ${payload.passengers}`, `Date: ${payload.date}`,
    `Pickup time: ${payload.time || 'To be arranged'}`, `Pickup: ${payload.pickup || 'To be arranged'}`,
    `Destination: ${payload.destination || 'To be arranged'}`,
  ];
  if (payload.message) lines.push('', 'The plan:', payload.message);
  lines.push('', 'Please confirm availability and provide a personalized quote.');
  return lines.join('\n');
}

const inquiryForm = $('#inquiry-form');
$$('#inquiry-form input, #inquiry-form textarea').forEach((input) => input.addEventListener('input', () => input.setCustomValidity('')));

function formStatus(message, type) {
  const status = $('#form-status');
  status.textContent = message;
  status.className = type;
  status.setAttribute('role', type === 'error' ? 'alert' : 'status');
  status.hidden = false;
  status.focus({ preventScroll: true });
}

inquiryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (sending || requestReceived) return;
  if (!inquiryForm.reportValidity()) return;
  const payload = Object.fromEntries([...new FormData(inquiryForm)].map(([key, value]) => [key, String(value).trim()]));
  if (payload.company_website) return;
  if (!payload.name) {
    $('#name').setCustomValidity('Please enter your name.');
    $('#name').reportValidity();
    return;
  }
  if (payload.phone.replace(/\D/g, '').length < 7) {
    $('#phone').setCustomValidity('Please enter a phone number where we can reach you.');
    $('#phone').reportValidity();
    return;
  }
  $('#form-status').hidden = true;

  if (previewMode) {
    const text = requestText(payload);
    $('#request-summary').textContent = text;
    $('#email-request').href = `mailto:Info@unisontransportation.com?subject=${encodeURIComponent(`Trip inquiry: ${payload.date} / ${payload.occasion}`)}&body=${encodeURIComponent(text)}`;
    $('#copy-status').textContent = '';
    $('#request-dialog').showModal();
    return;
  }

  sending = true;
  const submitButton = $('#submit-inquiry');
  submitButton.disabled = true;
  submitButton.textContent = 'Sending your request…';
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch('/api/quote', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal,
    });
    const result = await response.json().catch(() => null);
    const apiError = typeof result?.error === 'string' ? result.error.slice(0, 300) : '';
    if (!response.ok || apiError || result?.ok === false || result?.success === false) {
      throw new Error(apiError || 'The request could not be accepted. Please contact our concierge directly.');
    }
    if (result?.ok !== true && result?.success !== true) {
      const error = new Error('The service did not confirm receipt.');
      error.name = 'UnconfirmedDelivery';
      throw error;
    }
    requestReceived = true;
    formStatus('Your request has been received. Our concierge will contact you with availability and a personalized quote. No booking or payment has been made.', 'success');
    submitButton.textContent = 'Request received';
    const another = document.createElement('button');
    another.type = 'button';
    another.className = 'text-link';
    another.textContent = 'Start a new request';
    another.addEventListener('click', () => {
      requestReceived = false;
      inquiryForm.reset();
      $('#form-status').hidden = true;
      submitButton.disabled = false;
      submitButton.replaceChildren(document.createTextNode('Request your ride '), Object.assign(document.createElement('span'), { textContent: '↗' }));
      $('#name').focus();
    });
    $('#form-status').append(document.createElement('br'), another);
  } catch (error) {
    const message = error.name === 'AbortError' || error.name === 'UnconfirmedDelivery' || error instanceof TypeError
      ? 'Delivery could not be confirmed. Please call 629.259.5327 or email Info@unisontransportation.com before resending, so we can avoid a duplicate request.'
      : `${error.message} You can also call 629.259.5327 or email Info@unisontransportation.com.`;
    formStatus(message, 'error');
    submitButton.textContent = 'Request your ride ↗';
  } finally {
    window.clearTimeout(timeout);
    sending = false;
    if (!requestReceived) submitButton.disabled = false;
  }
});

$('#copy-request').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('#request-summary').textContent);
    $('#copy-status').textContent = 'Request copied. Paste it into an email when you’re ready.';
  } catch {
    $('#copy-status').textContent = 'Copying isn’t available in this browser. Select the request text above to copy it manually.';
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents($('#request-summary'));
    selection.removeAllRanges();
    selection.addRange(range);
  }
});

const now = new Date();
const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
$('#date').min = today;
$('#copyright-year').textContent = String(now.getFullYear());
$('#preview-note').hidden = !previewMode;
if (previewMode) {
  $('#submit-inquiry').replaceChildren(document.createTextNode('Review your request '), Object.assign(document.createElement('span'), { textContent: '↗' }));
  document.body.dataset.preview = 'true';
}

if (!reducedMotion.matches && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-revealed');
      observer.unobserve(entry.target);
    }
  }), { threshold: 0.07, rootMargin: '0px 0px 30px 0px' });
  $$('.reveal').forEach((element) => {
    element.classList.add('will-reveal');
    observer.observe(element);
  });
}
let scrollQueued = false;
function updateReadingProgress() {
  const height = document.documentElement.scrollHeight - window.innerHeight;
  $('.reading-progress').style.transform = `scaleX(${height > 0 ? Math.min(1, window.scrollY / height) : 0})`;
  scrollQueued = false;
}
window.addEventListener('scroll', () => {
  if (!scrollQueued) { scrollQueued = true; requestAnimationFrame(updateReadingProgress); }
}, { passive: true });
window.addEventListener('resize', updateReadingProgress);
updateReadingProgress();
// Enable submission only after all form safeguards have initialized.
$('#submit-inquiry').disabled = false;
