

angular.module('theta')


// custom events subclass
angular.module('theta').factory('ARPUDataService', function($window, ProductService, GraphDataService, $rootScope, $location, $http) {
  // create our new custom object that reuse the original object constructor
    
    var ARPUDataService = function() {
        
    };

    
    ARPUDataService.prototype.fetchData = function(startDate, endDate) {
        
        var chunks = $window.location.pathname.split('/');
        this.app_id = chunks[chunks.length-2];

        var url = this.getURLForArgs(["/ad-revenues/get_arpu_data", this.app_id ], startDate, endDate);
        
        var self = this;
        
        self.dataLoaded = false;
        $http.get(url, {}).then(function(response) {

            self.arpuData = response.data['arpu_data']
            
            self.dataLoaded = true;
            
            if (self.arpuData == null || self.arpuData.length < 1)
                self.dataEmpty = true;
            
            self.arpuMax  = response.data['max_arpu']
            for (var i in self.arpuData)
            {
                width = (self.arpuData[i]['arpu']/self.arpuMax)*100
                self.arpuData[i]['width'] = String(width)+"%";
                if (isNaN(width))
                    self.arpuData[i]['width'] = "0%"
            }
        });   
        
    };
        
    ARPUDataService.prototype.getURLForArgs = function(args, startDate, endDate)
    {
        var secondsStart = startDate.getTime() / 1000;
        var secondsEnd = endDate.getTime() / 1000;
        if (startDate == -1) {
                secondsStart = 0;
        }
        urlEnd = secondsStart + '/' + secondsEnd + '/';
        
        urlStart = ''
        for (i=0;i<args.length;i++)
            urlStart += args[i]+'/';
        
        return urlStart + urlEnd;
    };
        
    return ARPUDataService;

})

// ProductService,
.controller('arpu', function(ARPUDataService, DatePickerService,AppDetailsGraphDataService, $scope, $rootScope ) {
   
    $scope.datePickerService = new DatePickerService();
    $scope.datePickerService.initDate();
    
    $rootScope.arpuDataService = new ARPUDataService()
    
    //initial data fetching
    $rootScope.arpuDataService.fetchData($scope.datePickerService.date.startDate, $scope.datePickerService.date.endDate)
    
    // fetch customers apps
    //ProductService.fetchApps();
    $scope.graphData = new AppDetailsGraphDataService();
    
    
    //target an event when chosen date is changed
    $scope.$watch('datePickerService.date', function(newDate, oldDate) {
        if (oldDate == newDate) 
            return;        
        $rootScope.arpuDataService.fetchData(newDate.startDate, newDate.endDate)
    });  
    
    
});