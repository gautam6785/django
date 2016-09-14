// singleton to manage date for control on dashboard
angular.module('theta').factory('DatePickerService', function($location, $rootScope) {
  // for max on date picker
  var DatePickerService = function () {
    this.staticToday = new Date();
    this.defaultYesterday = true;
    // for date selector on dashboard
    this.initRanges();
    if($location.search().startDate > 0) {
      this.setRangeSelector($location.search().startDate,$location.search().endDate);
    }
    if (!this.range) {
      this.range = this.rangeLabels[1];
    }
  }

  DatePickerService.prototype.initRanges = function () {
    this.rangeLabels = [ {"label":"7 Days", "days":7}, 
                         {"label":"28 Days", "days":28},  
                         {"label":"84 Days", "days":84},  
                       ];
  }


  DatePickerService.prototype.initCompetitorRanges = function () {
    this.defaultYesterday = false;
    this.rangeLabels = [ {"label":"7 Days", "days":7}, 
                         {"label":"14 Days", "days":14},  
                         {"label":"28 Days", "days":28},  
                       ];
    this.range = this.rangeLabels[0];
  }


  DatePickerService.prototype.setRangeSelector = function(startDate, endDate) {
    var startDateMoment = moment(new Date(startDate));
    var endDateMoment = moment(new Date(endDate));
    var dayRange = startDateMoment.diff(endDateMoment, "days");
    var found = false;
    for (var i=0;i<this.rangeLabels.length;i++) {
      var l = this.rangeLabels[i];
      if (l.days == dayRange) {
        this.range = l;
        found = true;
        break;
      }
    }
  };


  DatePickerService.prototype.initDate = function() {
    var today = new Date();
    var yesterday = new Date(new Date().setDate(today.getDate()-1));
    var startDate;
    var endDate;
    startDate = new Date(new Date().setDate(today.getDate()-this.range.days));
    if (this.defaultYesterday) {
      endDate = yesterday;
    } else {
      endDate = today;
    }
    this.date = { startDate:startDate, 
                      endDate:endDate };
    this.setRangeSelector(this.date.startDate, this.date.endDate);
  };


    DatePickerService.prototype.fetchDataAndSetHash = function(range) {
	    var today = new Date();
	    var yesterday = new Date(new Date().setDate(today.getDate()-1));
	    var before = new Date(new Date().setDate(today.getDate()-range.days));
	    this.date = {startDate:before, 
	                   endDate:yesterday};
	    var search = $location.path('/').search();
	    search.startDate = yesterday.getTime();
	    search.endDate = before.getTime();
	    $location.path('/').search(search);
	    mixpanel.track("set range");
	    this.range = range;
  };
  
  return DatePickerService;

});
