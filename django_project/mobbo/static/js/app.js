angular.module('theta', ['ordinal', 'ui.bootstrap', 'ngCookies', 'daterangepicker', 'ui.grid', 'ui.grid.pagination','nvd3','datatables']).run(function($http, $cookies) {
    $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;

    mixpanel.track_links("#logo-link", "Click Nav", {"link":"Home"});
    mixpanel.track_links("#demo-link", "Click Nav", {"link":"Demo"});
    mixpanel.track_links("#rankings-link", "Click Nav", {"link":"Rankings"});
    mixpanel.track_links("#blog-link", "Click Nav", {"link":"Blog"});
    mixpanel.track_links("#user-menu-link", "Click Nav", {"link":"User Dropdown"});
    mixpanel.track_links("#user-menu-account", "Click Nav", {"link":"User - Account"});
    mixpanel.track_links("#user-menu-logout", "Click Nav", {"link":"User - Logout"});
    mixpanel.track_links("#login-link", "Click Nav", {"link":"Login - Mobile"});
    mixpanel.track_links("#home-signup-button", "Click Home Signup");
    mixpanel.track_links("#bottom-home-signup-button", "Click Home Signup", {"bottom":true});
    mixpanel.track_links("#home-dashboard-image", "Click Home Image");
    mixpanel.track_links(".developer-url", "Click Headshot");
    mixpanel.track_links(".developer-icon-url", "Click Developer Icon");
    mixpanel.track_links(".footer-link", "Click Footer Link", {"loggedIn":false});
    mixpanel.track_links(".loggedin-footer-link", "Click Footer Link", {"loggedIn":true});
    mixpanel.track_links("#dashboard-range-dropdown", "Click Range Dropdown", {"view":"Sales Dashboard"});
    mixpanel.track_links("#dashboard-date-selector", "Click Date Selector", {"view":"Sales Dashboard"});
    mixpanel.track_links("#ranks-range-dropdown", "Click Range Dropdown", {"view":"Rankings"});
    mixpanel.track_links("#ranks-date-selector", "Click Date Selector", {"view":"Rankings"});
    mixpanel.track_links(".company-name", "Click Company Name");
    mixpanel.track_links("#dashboard-signup-top", "Click Dashboard Signup");

})

.config(function() {
})


.filter('secondsToDateTime', [function() {
    return function(seconds) {
      var timeStr = moment(new Date('01-01-1970 UTC').setSeconds(seconds)).utc().fromNow();
      // trim "ago"
      return timeStr.substring(0, timeStr.length - 4); 
    };
}]);


