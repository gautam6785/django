angular.module('theta').factory('AppInfo', function($http, $location) {

var AppInfo = function() {
	this.platformImages = { "iOS": "/static/img/apple-bite.png",			
	"Android": "/static/img/android.png" };
	this.fetchedInfo = {};
	if($location.search().products && $location.search().products.length > 0) {
		this.selectedProducts = $location.search().products.split(",");
	}
};


  // returns the icon URL and stores the rest of the info in fetchedInfo
  AppInfo.prototype.fetchIcon  = function(bundle_id, platform) {
    var ANDROID_PLATFORM_ID = "Android";
    if (platform == ANDROID_PLATFORM_ID) {
      return this.fetchIconAndroid(bundle_id);
    }
    return this.fetchIconIos(bundle_id);
  };

  
  // request iOS metadata
  AppInfo.prototype.fetchIconIos = function(bundle_id) {
  	var url = "/dashboard/app_info/" + bundle_id + '/?z';
  	var self = this;
      // pre load, return
      return $http.get(url, {}).then(function(response) {
      // for bundles
      var data = response.data;
      if (!data[0] || data.error) {
      	self.fetchedInfo[bundle_id] = {};
      	self.fetchedInfo[bundle_id].name = bundle_id;
      	return "/static/img/blank.png";    
      }        
      self.fetchedInfo[bundle_id] = data[0].fields;
      return data[0].fields.icon_url;        
    });     
    };

	// request Android metadata
	AppInfo.prototype.fetchIconAndroid = function(bundle_id) {
		var url = "/dashboard/app_info_android/" + bundle_id + '/';
		var self = this;
		return $http.get(url, {}).then(function(response) {
			var data = response.data;
			if (!data[0]) {
				self.fetchedInfo[bundle_id] = {};
				return null;    
			}
			if (data[0].fields.error) {
				self.fetchedInfo[bundle_id] = {};
				return "/static/img/blank.png";
			}
			if (data[0].fields.icon_url) {
				var iconURL = data[0].fields.icon_url.substring(0, data[0].fields.icon_url.length - 3) + '57';
				self.fetchedInfo[bundle_id] = data[0].fields;
				return iconURL;        
			}
		});     
	};

  // set the company name from a random app in their list
  AppInfo.prototype.setCompanyName = function() {
  	for (var key in this.fetchedInfo) {
  		if (this.fetchedInfo[key] && this.fetchedInfo[key].sellerName ) {
  			this.companyName = this.fetchedInfo[key].sellerName;
  			break;
  		}
  		if (this.fetchedInfo[key] && this.fetchedInfo[key].developer) {
  			this.companyName = this.fetchedInfo[key].developer;
  			break;
  		}
  	}
  };


  AppInfo.prototype.categories = {
      "App Store": { 
                     types: [
                              'Top Grossing',
                              'Paid Downloads', 
                              'Free Downloads', 
                             ],
                     categories: [
                              {'name':'All Categories'},
                              {'name':'Books'},
                              {'name':'Business'},
                              {'name':'Catalogs'},
                              {'name':'Education'},
                              {'name':'Entertainment'},
                              {'name':'Finance'},
                              {'name':'Food & Drink'},
                              {
                               'name':'Games',
                               'subcategories': ['All', 'Arcade', 'Card']
                              },
                              {'name':'Health & Fitness'},
                              {'name':'Kids'},
                              {'name':'Lifestyle'},
                              {'name':'Medical'},
                              {'name':'Music'},
                              {'name':'Navigation'},
                              {'name':'News'},
                              {'name':'Newsstand'},
                              {'name':'Photo & Video'},
                              {'name':'Productivity'},
                              {'name':'Reference'},
                              {'name':'Social Networking'},
                              {'name':'Sports'},
                              {'name':'Travel'},
                              {'name':'Utility'},
                              {'name':'Weather'},
                             ],
                     countries: [
                              {'name':'United States'},
                              {'name':'Canada'},
                              {'name':'Germany'},
                              {'name':'France'},
                              {'name':'China'},
                              {'name':'India'},
                              {'name':'Brazil'},
                              {'name':'Italy'},
                              {'name':'Japan'},
                              {'name':'United Kingdom'},
                              {'name':'Spain'},
                              {'name':'Portugal'},
                              {'name':'Venezuela'},
                              {'name':'Mexico'},
                              {'name':'Thailand'},
                              {'name':'Russia'},
                              {'name':'Kazakhstan'},
                              {'name':'Ukraine'},
                              {'name':'Poland'},
                              {'name':'Austria'},
                              {'name':'Greece'},
                              {'name':'Greek Macdeonia'},
                              {'name':'Israel'},
                              {'name':'Iraq'},
                             ]
                   },    
      "Google Play": { 
                     types: [
                              'Top Grossing',
                              'Paid Downloads', 
                              'Free Downloads', 
                             ],
                     categories: [
                              {'name':'All Categories'},
                              {'name':'Books'},
                              {'name':'Business'},
                              {'name':'Catalogs'},
                              {'name':'Education'},
                              {'name':'Entertainment'},
                              {'name':'Finance'},
                              {'name':'Food & Drink'},
                              {
                               'name':'Games',
                               'subcategories': ['All', 'Arcade', 'Card']
                              },
                              {'name':'Travel'},
                             ],
                     countries: [
                              {'name':'United States'},
                              {'name':'Canada'},
                              {'name':'Germany'},
                              {'name':'France'},
                              {'name':'China'},
                              {'name':'India'},
                              {'name':'Brazil'},
                              {'name':'Italy'},
                              {'name':'Japan'},
                              {'name':'United Kingdom'},
                              {'name':'Spain'},
                              {'name':'Portugal'},
                              {'name':'Venezuela'},
                              {'name':'Mexico'},
                              {'name':'Thailand'},
                              {'name':'Russia'},
                              {'name':'Kazakhstan'},
                              {'name':'Ukraine'},
                              {'name':'Poland'},
                              {'name':'Austria'},
                              {'name':'Greece'},
                              {'name':'Greek Macdeonia'},
                              {'name':'Israel'},
                              {'name':'Iraq'},
                             ]
                   }    
    };
  return AppInfo;

});


