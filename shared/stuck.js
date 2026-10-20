// Shows a message when the page script does not start, so the page does not say "Loading…"
// for ever. This happens when the browser keeps an old copy of a shared file and the new
// page needs the new copy (GitHub Pages lets browsers keep files for 10 minutes), or when a
// file does not download. This is a classic script, not a module, so it runs even then.
// Each page script sets window.rdStarted = true as its first step.
addEventListener('error', () => {
  const p = document.getElementById('loading');
  if (window.rdStarted || !p) return;
  p.hidden = false;
  p.className = 'problem';
  p.setAttribute('role', 'alert');
  p.textContent = 'The page did not load. Reload the page. On a computer, press Ctrl+Shift+R (Mac: Cmd+Shift+R).';
}, true);   // true: also catches a file that does not download
