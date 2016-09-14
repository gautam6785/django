angular.module('theta')

// custom filter for showing percentages in templates
.filter('percentage', ['$filter', function ($filter) {
  return function (input, decimals) {
    return $filter('number')(input * 100, decimals) + '%';
  };
}])



// trigger graph resizes when the page resizes
/*.directive('resize', function ($window) {
    return function (scope, element) {
        scope.getWindowDimensions = function () {
            return {
                'h': element[0].clientHeight,
                'w': element[0].clientWidth
            };
        };
        scope.$watch(scope.getWindowDimensions, function (newValue, oldValue) {
          if (newValue.w != oldValue.x) {
            scope.windowHeight = newValue.h;
            scope.windowWidth = newValue.w;            
          }
        }, true);

        angular.element($window).bind('resize', function () {
          var width = scope.getWindowDimensions().w-30;
          if (scope.active && scope.active.ranks) {
            width = scope.getWindowDimensions().w - 700;
            scope.graphDataRanks.resizeGraphs(120, width);
            scope.$apply();
            return;
          } else if (series_name) {
            width-= 50;
          } else if (scope.theta_apps) {
            width = scope.getWindowDimensions().w - 30;
          } else if ($window.innerWidth >= 768) {
            width = scope.getWindowDimensions().w/3-30;
          }
          scope.graphData.resizeGraphs(120, width);
          scope.$apply();
        });
    };
});
*/
