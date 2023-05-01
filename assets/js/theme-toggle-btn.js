
// Set dark mode toggle button accordingly.



document.addEventListener("DOMContentLoaded", function (event) {
    // Check cache
    var theme_preference = localStorage.getItem("powermon-theme-pref");
    if (theme_preference == "dark") {
        enable_dark_mode();
    } else {
        enable_light_mode();
    }

    var current_theme = jtd.getTheme()
    var themeBtn = document.getElementById("dark-toggle-switch")
    if (themeBtn) {
        if (current_theme == "default" || current_theme == "powermon_light") {
            themeBtn.checked = false;
        } else if (current_theme == "powermon_dark") {
            themeBtn.checked = true;
        }
    }

    themeBtn.addEventListener("click", function() {
        if (this.checked == true) {
            enable_dark_mode();
        } else if (this.checked == false) {
            enable_light_mode();
        }
    })

    // Show body after theme is set.
    document.getElementsByTagName("body")[0].style.display = "unset" 
    
})


function enable_dark_mode() {
    var themeBtn = document.getElementById("dark-toggle-switch");
    themeBtn.checked = true;
    jtd.setTheme("powermon_dark")
    localStorage.setItem("powermon-theme-pref", "dark");
}

function enable_light_mode() {
    var themeBtn = document.getElementById("dark-toggle-switch");
    themeBtn.checked = false;
    jtd.setTheme("powermon_light")
    localStorage.setItem("powermon-theme-pref", "light");

}