// Theme toggle, subgenre filter, and one audio preview at a time.
(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme");
  function isDark() {
    var set = root.dataset.theme;
    return set ? set === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function label() {
    toggle.textContent = isDark() ? "Light theme" : "Dark theme";
  }
  toggle.addEventListener("click", function () {
    var next = isDark() ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
    label();
  });
  label();

  var chips = document.querySelectorAll(".chip");
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var tag = chip.dataset.tag;
      chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c === chip)); });
      document.querySelectorAll(".patch").forEach(function (patch) {
        patch.hidden = tag !== "" && patch.dataset.tags.split(" ").indexOf(tag) === -1;
      });
    });
  });

  var tip = document.getElementById("tip");
  if (tip) {
    document.querySelectorAll(".dot").forEach(function (dot) {
      function show() {
        tip.textContent = dot.dataset.tip;
        tip.hidden = false;
        var box = dot.getBoundingClientRect();
        tip.style.left = Math.min(box.left + window.scrollX, window.innerWidth - tip.offsetWidth - 12) + "px";
        tip.style.top = (box.top + window.scrollY - tip.offsetHeight - 6) + "px";
      }
      function hide() { tip.hidden = true; }
      dot.addEventListener("pointerenter", show);
      dot.addEventListener("pointerleave", hide);
      dot.addEventListener("focus", show);
      dot.addEventListener("blur", hide);
    });
  }

  document.addEventListener("play", function (event) {
    document.querySelectorAll("audio").forEach(function (audio) {
      if (audio !== event.target) audio.pause();
    });
  }, true);
})();
