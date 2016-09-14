
angular.module('theta').factory('BreakdownPickerService', function($location, $rootScope) {
    
    var BreakdownPickerService = function()
    {
        this.currentBreakdown = 'country'
    }
 
       
    BreakdownPickerService.prototype.breakdownChange = function( breakdownBy )
    {
        if (breakdownBy == 'platform')
        {
            //set data url to appbreakdown
            this.currentBreakdown = 'platform';
        }
        else if (breakdownBy == 'country')
        {
            //set data url to country
            this.currentBreakdown = 'country';
        }
        else
            this.currentBreakdown = 'Error'
    }
    
    return BreakdownPickerService;
    
});