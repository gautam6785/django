/*global moment:true, developer_mode:true, sdk_versions:true, django_user:true */

angular.module('theta')

// controller for dasdhboard and drilldowns, itunes_accounts:true
.controller('GraphController', function(ProductService, CountryInfoService, DatePickerService, $location, $timeout, $scope, $http, $window, $rootScope, $modal, $log, GraphDataService) {

  $scope.initSuperClass = function () {
	  
    $scope.datePickerService = new DatePickerService();
    $scope.datePickerService.initDate();

    // fetch customers apps
    ProductService.fetchApps();

    // fetch country info
    CountryInfoService.fetchCountryInfo();

    $rootScope.$on('productsUpdated', function(){
      $scope.fetchDataIfProducts($scope.graphData);
      if (!$scope.pollEnded && $scope.user) {
          $scope.pollForNewAccountData();
      }
    });
  };


  $scope.endDateString = function () {
   var endDate = $scope.datePickerService.date.endDate;

    var today = moment();
    var daysPassed = moment(today).diff(endDate, 'days');
    if(daysPassed === 0) {
      return "Today";      
    }
    if(daysPassed == 1) {
      return "Yesterday";      
    }
    return moment(new Date(endDate)).fromNow();
  };


  $scope.fetchDataIfProducts = function (graphData) {
    // as soon as products arrive, fetch some graph data
    if (ProductService.productIDString) {
      graphData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
    } else {
      // show controls, user doesn't have products yet
      graphData.dataLoaded = true;
    }    
  };
  

});


angular.module('theta')



// for pages detailing each public app
.controller('AppDetailsGraphController',  function ($http, $modal, ProductService, CountryInfoService, $window, $rootScope, AppDetailsGraphDataService, $controller, $scope) {
  $controller('GraphController', {$scope: $scope});
  $scope.initSuperClass();
  var chunks = $window.location.pathname.split('/');
  $scope.graphData = new AppDetailsGraphDataService();
  $scope.graphData.app_id = chunks[chunks.length-3];
  $scope.graphData.country = [chunks[chunks.length-2]];
  
  //CountryInfoService.fetchCountryInfo();
  
  $scope.activeGraphData = $scope.graphData; 
  $scope.app = app;
  $scope.selectedCountry = "All Countries";

  $scope.$watch('datePickerService.date', function(newDate, oldDate) {
   if (oldDate == newDate) return;
   $scope.activeGraphData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
  });    

  $scope.openCountryPopover = function (size) {
    mixpanel.track("open country popover");
    $modal.open({
      templateUrl: 'country_popover.html',
      controller: 'ProductsModalInstanceCtrl',
      windowClass: 'app-modal-window',
      size: size,
      resolve: {
        graphData: function () {
          return $scope.graphData;
        }
      }
    });
  };


  $rootScope.fetchDataForCountry = function (country) {
	var selectedcountryName = [];
	var selectedcountryId = [];

	for (var i=0; i < country.length; i++) {
	    selectedcountryName.push(country[i].name);
	    selectedcountryId.push(country[i].id); 
    }
    
    if(selectedcountryName.length == 1){
		$scope.selectedCountry = selectedcountryName[0];	
    }
    else{
		var countryLength = selectedcountryName.length;
		$scope.selectedCountry = countryLength+' Countries';
	}
	
    $scope.activeGraphData.country = selectedcountryId;
    $scope.activeGraphData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
    $rootScope.$emit('closeCountryModal');
  }
  
  
  $scope.getChecked = function(country_code){
    
    var idx = $scope.activeGraphData.selectedCountryCode.indexOf(country_code);
    if (idx > -1) {
		return true;
    }else {
		return false;
	}
  };
  
})



// for pages detailing each public app
.controller('AppDownloadGraphController',  function ($http, $modal, ProductService, CountryInfoService, $window, $rootScope, AppDownloadGraphDataService, $controller, $scope) {
  $controller('GraphController', {$scope: $scope});
  $scope.initSuperClass();
  var chunks = $window.location.pathname.split('/');
  $scope.graphData = new AppDownloadGraphDataService();
  $scope.graphData.app_id = chunks[chunks.length-3];
  $scope.graphData.country = [chunks[chunks.length-2]];
  
  $scope.activeGraphData = $scope.graphData; 
  $scope.app = app;
  $scope.selectedCountry = "All Countries";

  $scope.$watch('datePickerService.date', function(newDate, oldDate) {
   if (oldDate == newDate) return;
   $scope.activeGraphData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
  });    

 
  $scope.openCountryPopover = function (size) {
    mixpanel.track("open country popover");
    $modal.open({
      templateUrl: 'country_popover.html',
      controller: 'ProductsModalInstanceCtrl',
      windowClass: 'app-modal-window',
      size: size,
      resolve: {
        graphData: function () {
          return $scope.graphData;
        }
      }
    });
  };


   $rootScope.fetchDataForCountry = function (country) {
		var selectedcountryName = [];
		var selectedcountryId = [];

		for (var i=0; i < country.length; i++) {
			selectedcountryName.push(country[i].name);
			selectedcountryId.push(country[i].id); 
		}
		
		if(selectedcountryName.length == 1){
			$scope.selectedCountry = selectedcountryName[0];	
		}
		else{
			var countryLength = selectedcountryName.length;
			$scope.selectedCountry = countryLength+' Countries';
		}
		
		$scope.activeGraphData.country = selectedcountryId;
		$scope.activeGraphData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
		$rootScope.$emit('closeCountryModal');
    }
	
	$scope.getChecked = function(country_code){
		var idx = $scope.activeGraphData.selectedCountryCode.indexOf(country_code);
		if (idx > -1) {
			return true;
		}else {
			return false;
		}
    };
  
 
})



// the product popover
.controller('ProductsModalInstanceCtrl', function (CountryInfoService, DatePickerService, $rootScope, $scope, $modalInstance, graphData) {
  
	$scope.CountryInfoService = CountryInfoService;
	$scope.graphData = graphData;
	$scope.cancel = function () {
		$modalInstance.dismiss('cancel');
	};
	
	$rootScope.$on('closeCountryModal', function(){
		$modalInstance.dismiss('cancel');
	})

	$scope.selection=[];
	countryData = graphData.allcountryArrays;
	
	for (var cid in countryData) {
		if(countryData[cid].checked){
			var dict = countryData[cid];
		    $scope.selection.push(dict);
		}                
    }
	
   // toggle selection for a given country by id
    $scope.toggleSelection = function toggleSelection(country) {
		var countries = $scope.graphData.all_countries;
	    var idx = $scope.selection.indexOf(country);
	    // is currently selected
	    if (idx > -1) {
	      $scope.selection.splice(idx, 1);
	    }
	    // is newly selected
	    else {
			if(country.id == 'ALL'){
				$scope.selection = [];
			    for (var key in countries) {
					if(key != 'ALL') {
						countries[key].checked = false;
						countries[key].checkedOverall = false;
					}else {
						countries[key].checked = true;
						countries[key].checkedOverall = true;
					}
				}	
			} else {
				for (var key in countries) {
					if(key == 'ALL') {
						countries[key].checked = false;
						countries[key].checkedOverall = false;
					}
				}	
				for (var i=0;i<this.selection.length;i++) {
					if(this.selection[i].id == 'ALL'){
					    $scope.selection.splice(this.selection[i], 1);
					}
				}				
			}
			$scope.selection.push(country);
	    }
	    
    }
});


angular.module('theta')
.controller('AppController', function(DatePickerService, $location, $timeout, $scope, $http, $window, $rootScope, $modal, $log, AppService) {

  $scope.initSuperClass = function () {
	  
    $scope.datePickerService = new DatePickerService();
    $scope.datePickerService.initDate();
    
   };

  $scope.endDateString = function () {
   var endDate = $scope.datePickerService.date.endDate;

    var today = moment();
    var daysPassed = moment(today).diff(endDate, 'days');
    if(daysPassed === 0) {
      return "Today";      
    }
    if(daysPassed == 1) {
      return "Yesterday";      
    }
    return moment(new Date(endDate)).fromNow();
  };

});

angular.module('theta')
.controller('AppDetailsController', function(DatePickerService, AppDetailService, $location, $timeout, $scope, $http, $window, $rootScope, $modal, $log, $controller, DTOptionsBuilder, DTColumnBuilder) {
	
	$controller('AppController', {$scope: $scope});
	$scope.initSuperClass();
  
	$scope.appData = new AppDetailService();
	$scope.activeAppData = $scope.appData;
	$scope.activeAppData.platform_type = 'all';
	$scope.activeAppData.activeMenu = 'all';
	
	
	$scope.$watch('datePickerService.date', function(newDate, oldDate) {
		if (oldDate == newDate) return;
		$scope.activeAppData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
	});  
	
	$scope.activeAppData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
	
	$scope.dtOptions = {
		autoWidth: false,
		paging: true,
		dom: 'lfrtip',
		pageLength: 25,
		pagingType: "full_numbers"
	};

	$rootScope.fetchDataForplatform = function (platform) {
		$scope.activeAppData.platform_type = platform;
		$scope.activeAppData.activeMenu = platform;
		$scope.activeAppData.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate);
    }
	
	
})
