// load Angular
require('angular');  
// load the main app file
var appModule = require('../../web-app');  
// replaces ng-app="appName"
angular.element(document).ready(function () {  
  angular.bootstrap(document.getElementById('base_body'), [appModule.name], {
    //strictDi: true
  });
});