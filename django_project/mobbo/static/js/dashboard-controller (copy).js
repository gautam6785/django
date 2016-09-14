/*global moment:true, developer_mode:true, sdk_versions:true, django_user:true */

angular.module('theta')
// for pages detailing each public app

// controller for dasdhboard and drilldowns, itunes_accounts:true
.controller('GraphController', function(DatePickerService, $location, $timeout, $scope, $http, $window, $rootScope, $modal, $log, GraphDataService, GraphAppService) {
	
	$scope.initSuperClass = function () {
   
    $scope.datePickerService = new DatePickerService();
    $scope.datePickerService.initDate();
    
    var chunks = $window.location.pathname.split('/');
    $scope.app_id = chunks[chunks.length-2];
    
    GraphAppService.getApp($scope.app_id,$scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate).then(function(response){
        
		$scope.highchartsNG = {
				chart: {
					type: 'spline'
				},
				title: {
					text: 'Snow depth at Vikjafjellet, Norway'
				},
				subtitle: {
					text: 'Irregular time data in Highcharts JS'
				},
				xAxis: {
					type: 'datetime',
					dateTimeLabelFormats: { // don't display the dummy year
						month: '%e. %b',
						year: '%b'
					},
					title: {
						text: 'Date'
					}
				},
				yAxis: {
					title: {
						text: 'Snow depth (m)'
					},
					min: 0
				},
				tooltip: {
					headerFormat: '<b>{series.name}</b><br>',
					pointFormat: '{point.x:%e. %b}: {point.y:.2f} m'
				},

				plotOptions: {
					spline: {
						marker: {
							enabled: true
						}
					}
				},
				
				
				chart: {
						type: 'spline'
					},
				xAxis: {
						categories: response.data.label
					},
				yAxis: {
					title: {
						text: 'Income'
					},
					plotLines: [{
						value: 0,
						width: 1,
						color: '#808080'
					}]
				},
				
				series: response.data.graphdata,
				
				legend: {
					layout: 'vertical',
					align: 'right',
					verticalAlign: 'middle',
					borderWidth: 0
                },
                
				title: {
						text: 'Sales Revenue Data',
						x: -20 //center
                },
		}
        
    });
    
    
     
  };
  
});

angular.module('theta')
.controller('AppDetailsGraphController',  function ($http, $modal, $window, $rootScope, $controller, $scope, AppDetailsGraphDataService, GraphAppService) {
	$controller('GraphController', {$scope: $scope});
	$scope.initSuperClass();
	
	var chunks = $window.location.pathname.split('/');
	$scope.graphData = new AppDetailsGraphDataService();
	$scope.graphData.app_id = chunks[chunks.length-2];
	$scope.activeGraphData = $scope.graphData; 
	$scope.app = app;
	$scope.selectedCountry = "United States";
	
	$scope.$watch('datePickerService.date', function(newDate, oldDate) {
		   if (oldDate == newDate) return;
		   $scope.activeGraphData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
    });
    
  	  
})
