/* global thetaUtil:true */

// singleton to fetch and manage customer's products/apps
angular.module('theta').service('ProductService', function(AppInfo, $rootScope, $location, $http) {

	this.fetchApps = function() {
		if (!this.appInfo) {
		  // for fetching icons and names of apps
      this.appInfo = new AppInfo();
      this.fetchedInfo = this.appInfo.fetchedInfo;
		}
		var products_url = "/dashboard/get_products/";
		var self = this;
		$http.get(products_url, {}).then(function(response){
			var productIDString = response.data.product_string;
			self.productIDString = productIDString;
			$rootScope.$emit('productsUpdated');
	  });
	};

  // select products based on URL hash if set
  if($location.search().products && 
  	$location.search().products.length > 0) {
  	this.selectedProducts = $location.search().products.split(",");
  }

});

angular.module('theta').service('CountryInfoService', function($rootScope, $location, $http) {

	this.fetchCountryInfo = function() {
		var url = "/dashboard/get_country_list/";
		var self = this;
		$http.get(url, {}).then(function(response){
			self.country = response.data;
			self.selectDefaults(self.country);
		}); 
	};

    // set variables to show country menu
    this.selectDefaults = function(country){
        this.selectedCountry = country;
        for (var i=0;i<this.selectedCountry.length;i++) {
			var country = this.selectedCountry[i];
			 if (country.name == "All Countries") {
				this.selectedCountry = country;
				break;
			 }
		} 
	};
	
	
});


angular.module('theta').factory('AppService', function(DatePickerService, $window, $rootScope, $location, $http) {

	var AppService = function () {
		
	};

	AppService.prototype.fetchData = function(startDate, endDate) {
		var url = this.dataURLForBase("/dashboard/graph_data", startDate, endDate);
		var self = this;
		$http.get(url, {}).then(function(response) {
			self.dataLoaded = true;
			//self.storeDataAndRefreshGraphs(response.data);
			//$rootScope.$emit('graphDataUpdated');
		});     
	};


	AppService.prototype.dataURLForBase = function(base, startDate, endDate) {
		
		//alert(startDate);
		var secondsStart = startDate.getTime() / 1000;
		var secondsEnd = endDate.getTime() / 1000;
		if (startDate == -1) {
			secondsStart = 0;
		}
		return base + '/' + secondsStart + '/' + secondsEnd + '/';
	};


  return AppService;
});



angular.module('theta').factory('AppDetailService', function(AppService,$rootScope, $location, $http) {
	var AppDetailService = function () {
		AppService.apply(this, arguments);
	};
	AppDetailService.prototype = new AppService();
	AppDetailService.prototype.dataURLForBase = function(base, platform_type, startDate, endDate) {
		var secondsStart = startDate.getTime() / 1000;
		var secondsEnd = endDate.getTime() / 1000;
		if (startDate == -1) {
			secondsStart = 0;
		}
		return base + '/' + platform_type + '/' + secondsStart + '/' + secondsEnd + '/';
	};
		
	AppDetailService.prototype.fetchData = function(startDate, endDate) {
		
		var url = this.dataURLForBase("/dashboard/app_list", this.platform_type, startDate, endDate);
		var self = this;
		self.dataLoaded = false;
		$http.get(url, {}).then(function(response) {
			self.dataLoaded = true;
			self.storeDataAndRefreshApps(response.data);
			//$rootScope.$emit('graphDataUpdated');
		});  
	};
	
	AppDetailService.prototype.storeDataAndRefreshApps = function (data) {
		this.raw_data = JSON.parse(JSON.stringify(data));
		//this.refreshCountires();
		//this.refreshGraphs();    
	};
	
	return AppDetailService;

});


angular.module('theta').factory('GraphDataService', function(DatePickerService, ProductService, CountryInfoService, $window, $rootScope, $location, $http) {

	var GraphDataService = function () {
    this.platformImages = { "iOS": "/static/img/apple-bite.png",
                            "Android": "/static/img/android.png" };
    this.appInfo = ProductService.appInfo;                           

	};

	GraphDataService.prototype.fetchData = function(startDate, endDate) {
		var url = this.dataURLForBase("/dashboard/graph_data", ProductService.productIDString, startDate, endDate);
		var self = this;
		$http.get(url, {}).then(function(response) {
			self.dataLoaded = true;
			self.storeDataAndRefreshGraphs(response.data);
			$rootScope.$emit('graphDataUpdated');
		});     
	};


	GraphDataService.prototype.dataURLForBase = function(base, productIDString, startDate, endDate) {
		
		//alert(startDate);
		var secondsStart = startDate.getTime() / 1000;
		var secondsEnd = endDate.getTime() / 1000;
		if (startDate == -1) {
			secondsStart = 0;
		}
		return base + '/' + productIDString + '/'  + secondsStart + '/' + secondsEnd + '/';
	};


  return GraphDataService;
});

// custom events subclass
angular.module('theta').factory('AppDetailsGraphDataService', function($window, ProductService, GraphDataService, $rootScope, $location, $http) {
  // create our new custom object that reuse the original object constructor
    var AppDetailsGraphDataService = function() {
  	  GraphDataService.apply(this, arguments);
    };

    AppDetailsGraphDataService.prototype = new GraphDataService();

    AppDetailsGraphDataService.prototype.fetchData = function(startDate, endDate) {
	
		var url = this.dataURLForBase("/dashboard/graph_data_app", this.country + '/' + this.app_id, startDate, endDate);
		var self = this;
		self.dataLoaded = false;
		$http.get(url, {}).then(function(response) {
			self.dataLoaded = true;
			self.storeDataAndRefreshGraphs(response.data);
			//$rootScope.$emit('appDetailsGraphDataUpdated');
		});     
	};

	AppDetailsGraphDataService.prototype.storeDataAndRefreshGraphs = function (data) {
		this.raw_data = JSON.parse(JSON.stringify(data));
		this.refreshCountires();
		this.refreshGraphs();    
	};
	
	
	 // chunk for display in bootstrap grid
    AppDetailsGraphDataService.prototype.chunkCountriesForDisplay = function() {
		this.allcountryArrays = [];
		this.selectedCountryCode = [];
		
		for (var cid in this.chart_data) {
			code = this.chart_data[cid].country_code;
			if(code != 'Other'){
				this.selectedCountryCode.push(this.chart_data[cid].country_code); 
			}
		}
		
        for (var cid in this.all_countries) {
			var dict = this.all_countries[cid];
			dict.country_id = cid;
			this.allcountryArrays.push(dict);                    
        }
       
        this.allcountryArrays.sort(compare);
	};
	
	function compare(a,b) {
		if (a.name < b.name)
			return -1;
		if (a.name > b.name)
			return 1;
		return 0;
	}
	
	
	// break the country info out of the raw-data for structuring the UI
	AppDetailsGraphDataService.prototype.refreshCountires = function() {
		var data = this.raw_data;
		this.chart_data = data.chartData   
		this.all_countries = data.all_country_info;
		this.enableCountries();
		this.chunkCountriesForDisplay();    
	};
	
	
	 // display countires if checked
	AppDetailsGraphDataService.prototype.enableCountries = function() {
		for (var key in this.all_countries) {
			this.all_countries[key].checked = false;
			this.all_countries[key].checkedOverall = false;
			var idx = this.country.indexOf(key.toString());
			if (idx > -1) {
				this.all_countries[key].checked = true;
  			    this.all_countries[key].checkedOverall = true;
  			    
			}
		}
		
	};


	// display all graphs
	AppDetailsGraphDataService.prototype.refreshGraphs = function() {
		var data = JSON.parse(JSON.stringify(this.raw_data));
		
		
		this.graphs = {	
			options: {
				chart: {
					type: 'stackedAreaChart',
					height: 350,
					margin : {
						top: 20,
						right: 20,
						bottom: 30,
						left: 40
					},
					padding:40,
					x: function(d){return d[0];},
					y: function(d){return d[1];},
					useVoronoi: false,
					clipEdge: false,
					duration: 100,
					padData: false,
					pointSize: 0,
					showControls: false,
					showLegend:true,
					showVoronoi:false,
					useInteractiveGuideline: true,
					xAxis: {
						showMaxMin: false,
						tickFormat: function(d) {
							return d3.time.format('%b %d')(new Date(d));
						}
					},
					yAxis: {
						tickFormat: function(d) {
							return '$' + d3.format(',.2f')(d);
						}
					},
					interactiveLayer: {
						tooltip: {
							headerFormatter: function(d) {
								return "Date: " + d3.time.format('%a, %b %d, %Y')(new Date(d));
							}							
						}
						
					}
                }
				
			},
			data: data.chartData
		}
		
	};

	return AppDetailsGraphDataService;

});


// custom events subclass
angular.module('theta').factory('AppDownloadGraphDataService', function($window, ProductService, GraphDataService, $rootScope, $location, $http) {
  // create our new custom object that reuse the original object constructor
    var AppDownloadGraphDataService = function() {
  	  GraphDataService.apply(this, arguments);
    };

    AppDownloadGraphDataService.prototype = new GraphDataService();
    AppDownloadGraphDataService.prototype.fetchData = function(startDate, endDate) {
	
		var url = this.dataURLForBase("/dashboard/graph_data_app_download", this.country + '/' + this.app_id, startDate, endDate);
		var self = this;
		self.dataLoaded = false;
		$http.get(url, {}).then(function(response) {
			self.dataLoaded = true;
			self.storeDataAndRefreshGraphs(response.data);
		});     
	};

	AppDownloadGraphDataService.prototype.storeDataAndRefreshGraphs = function (data) {
		this.raw_data = JSON.parse(JSON.stringify(data));
		this.refreshCountires();
		this.refreshGraphs();    
	};
	
	
	 // chunk for display in bootstrap grid
    AppDownloadGraphDataService.prototype.chunkCountriesForDisplay = function() {
		this.allcountryArrays = [];
		this.selectedCountryCode = [];
		
		for (var cid in this.chart_data) {
			code = this.chart_data[cid].country_code;
			if(code != 'Other'){
				this.selectedCountryCode.push(this.chart_data[cid].country_code); 
			}
		}
		
        for (var cid in this.all_countries) {
			var dict = this.all_countries[cid];
			dict.country_id = cid;
			this.allcountryArrays.push(dict);                    
        }
       
        this.allcountryArrays.sort(compare);
	};
	
	function compare(a,b) {
		if (a.name < b.name)
			return -1;
		if (a.name > b.name)
			return 1;
		return 0;
	}
	
	
	// break the country info out of the raw-data for structuring the UI
	AppDownloadGraphDataService.prototype.refreshCountires = function() {
		var data = this.raw_data;
		this.chart_data = data.chartData   
		this.all_countries = data.all_country_info;
		this.enableCountries();
		this.chunkCountriesForDisplay();    
	};
	
	
	 // display countires if checked
	AppDownloadGraphDataService.prototype.enableCountries = function() {
		for (var key in this.all_countries) {
			this.all_countries[key].checked = false;
			this.all_countries[key].checkedOverall = false;
			var idx = this.country.indexOf(key.toString());
			if (idx > -1) {
				this.all_countries[key].checked = true;
  			    this.all_countries[key].checkedOverall = true;
  			    
			}
		}
		
	};


	// display all graphs
	AppDownloadGraphDataService.prototype.refreshGraphs = function() {
		var data = JSON.parse(JSON.stringify(this.raw_data));
		
		
		this.graphs = {	
			options: {
				chart: {
					type: 'stackedAreaChart',
					height: 450,
					margin : {
						top: 20,
						right: 20,
						bottom: 30,
						left: 40
					},
					padding:40,
					x: function(d){return d[0];},
					y: function(d){return d[1];},
					useVoronoi: false,
					clipEdge: true,
					duration: 100,
					padData: false,
					pointSize: 0,
					showControls: false,
					showLegend:true,
					showVoronoi:false,
					useInteractiveGuideline: true,
					xAxis: {
						showMaxMin: false,
						tickFormat: function(d) {
							return d3.time.format('%b %d')(new Date(d));
						}
					},
					interactiveLayer: {
						tooltip: {
							headerFormatter: function(d) {
								return "Date: " + d3.time.format('%a, %b %d, %Y')(new Date(d));
							}							
						}
						
					}
                }
				
			},
			data: data.chartData
		}
		
	};

	return AppDownloadGraphDataService;

});
