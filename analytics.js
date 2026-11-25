// Preserve the existing analytics integration only on the live business domain.
// Local and staging previews never send analytics events.
if (location.hostname === 'unisontransportation.com') {
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  const script = document.createElement('script');
  script.src = '/_vercel/insights/script.js';
  script.defer = true;
  document.head.append(script);
}
