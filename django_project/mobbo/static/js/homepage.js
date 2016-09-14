/* global thetaUtil:true */

var theta_apps;
angular.module('theta')

// the product popover
.controller('HomePageController', function ($window, ProductService, $scope, GraphDataService, $rootScope, $window, $http) {
  // remove the overlay, and unmute the video

  $scope.newSeries = function() {
    return [ 
                   
                   { 
                     color: thetaUtil.MAIN_COLOR, 
                     data:[],
                     name:'top'
                   }
                 ];
  };

  $scope.init = function() {
   // $.material.init();
    ProductService.fetchApps();
    $scope.seriesData = $scope.newSeries();

   $scope.options = { 
                  "stroke":true, 
                  "min":'auto', 
                  "preserve":true, 
                  "width":0, 
                  "height":250, 
                  "renderer": 'bar',
                  "padding": {"top": 0.07, "left": 0.02, "right": 0.02, "bottom":0.07}
                };

   $scope.features = { 
                  "directive":{'watchAllSeries':true}, 
                     };

  $scope.throughput = {'series':$scope.seriesData, 'name':"Home Page", 
                         'options':$scope.options, 'features':$scope.features};


  $scope.graphData = new GraphDataService();
  if (theta_devs) {
    $scope.theta_devs = theta_devs;
    for (var i=0;i<$scope.theta_devs.length;i++) {
       ProductService.appInfo.fetchIcon(theta_devs[i].main_app.id, theta_devs[i].main_app.platform).then(function() {
      });
    }    
  }
  if (theta_apps) {
    $scope.theta_apps = theta_apps;
    for (var i=0;i<$scope.theta_apps.length;i++) {
       ProductService.appInfo.fetchIcon(theta_apps[i].id, theta_apps[i].platform).then(function() {
      });
    }    
  }
  $scope.graphData.graphs = [$scope.throughput];


  angular.element(window).bind('load', function() {
    if (test_homepage) {
      return;
    }
    var width = $scope.getWindowDimensions().w - 30;
      $scope.graphData.resizeGraphs(0, width);
      $scope.$apply();
      $scope.initGraph();    
    });  
  };


  $scope.hasAnimated = false;
  $scope.reloadGraph = function () {
    if ($scope.hasAnimated) {
      return;
    }
    $scope.seriesData = $scope.newSeries();
    $scope.throughput = {'series':$scope.seriesData, 'name':"Home Page", 
                         'options':$scope.options, 'features':$scope.features};

    $scope.graphData = new GraphDataService();
    $scope.graphData.graphs = [$scope.throughput];
    var width = $scope.getWindowDimensions().w;
    $scope.graphData.resizeGraphs(0, width);
    $scope.renderGraph(); 
    $scope.hasAnimated = true;
  };


$scope.firstSeries = [{'x':0, 'y':201},
                    {'x':1, 'y':230},
                    {'x':2, 'y':235},
                    {'x':3, 'y':225},
                    {'x':4, 'y':235},
                    {'x':5, 'y':255},
                    {'x':6, 'y':265},
                    {'x':7, 'y':260},
                    {'x':8, 'y':285},
                    {'x':9, 'y':305},
                    {'x':10, 'y':330},
                    {'x':11, 'y':335},
                    {'x':12, 'y':375},
                    {'x':13, 'y':370},
                    {'x':14, 'y':400},
                    {'x':15, 'y':460},
                    {'x':16, 'y':450},
                    {'x':17, 'y':500},
                    {'x':18, 'y':540},
                    {'x':19, 'y':680},
                    {'x':20, 'y':660},
                    {'x':21, 'y':650},
                    {'x':22, 'y':700},
                    {'x':23, 'y':860},
                    {'x':24, 'y':860},
                    {'x':25, 'y':850},
                    {'x':26, 'y':840},
                    {'x':27, 'y':875},
                    ];

  $scope.initGraph = function() {

    var first_series = $scope.firstSeries;
    for (var i=0;i<first_series.length;i++) {
      var oldSeries = $rootScope.littleGraphs[0].series[0];
      oldSeries.data.push(first_series[i]);
      oldSeries = jQuery.extend(true, {}, oldSeries);
    }
    $rootScope.littleGraphs[0].render();
    $scope.$apply();
  };

  

  $scope.renderGraph = function() {
    var first_series = $scope.firstSeries;
    var bump = 0;
    var timer = setInterval( function() {
      var oldSeries = $rootScope.littleGraphs[0].series[0];
      oldSeries.data.push(first_series[bump]);
      oldSeries = jQuery.extend(true, {}, oldSeries);
      $rootScope.littleGraphs[0].render();
      $scope.$apply();
      bump++;
      if (bump == first_series.length) {
        clearInterval(timer);
      }
    }, 20 );
  };

  $scope.playVideo = function() {
    $('video').get(0).currentTime = 0; 
    $('video').prop('muted', false);
    $('.covervid-video').css('opacity', 1);
    $('.fadeIn').css('display', 'none');
    $('.covervid-video').css('filter', 'none');
    $('.covervid-video').css('-webkit-filter', 'none');
  };


//resize the graphs and redisplay the slider after new data is fetched
  $rootScope.$on('graphDataUpdated', function(){
    var width = $scope.getWindowDimensions().w - 30;
    $scope.graphData.resizeGraphs(0, width);
  });


  $rootScope.graph_rendered = function(graph) {
    $rootScope.littleGraphs = [];
    $rootScope.littleGraphs.push(graph);
  };


  $scope.nameForApp = function(key) {
    if (ProductService.appInfo.fetchedInfo[key]) {
      return ProductService.appInfo.fetchedInfo[key].name;      
    }
    return "Unknown Name";      
  };

  $scope.iconForApp = function(key) {
    if (ProductService.appInfo.fetchedInfo[key]) {
      return ProductService.appInfo.fetchedInfo[key].icon_url;      
    }
    return "/static/img/blank.png";      
  };


  $scope.init();
});