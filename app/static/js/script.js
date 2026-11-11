document.addEventListener("DOMContentLoaded", function () {
    const tombol = document.getElementById("mobileMenuToggle");
    const sidebar = document.getElementById("studentSidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (!tombol || !sidebar || !overlay) return;

    function bukaMenu() {
        sidebar.classList.add("is-open");
        overlay.classList.add("is-visible");
        tombol.setAttribute("aria-expanded", "true");
        document.body.style.overflow = "hidden";
    }

    function tutupMenu() {
        sidebar.classList.remove("is-open");
        overlay.classList.remove("is-visible");
        tombol.setAttribute("aria-expanded", "false");
        document.body.style.overflow = "";
    }

    tombol.addEventListener("click", function () {
        sidebar.classList.contains("is-open")
            ? tutupMenu()
            : bukaMenu();
    });

    overlay.addEventListener("click", tutupMenu);

    sidebar.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", tutupMenu);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") tutupMenu();
    });
});
