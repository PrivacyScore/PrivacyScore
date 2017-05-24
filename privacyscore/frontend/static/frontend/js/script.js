var apiUrl = "https://privacyscore.org/api";

function getUrlVars() {
	var vars = {};
	var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
	vars[key] = value;
	});
	return vars;
}

function scrollTo(id) {
	var node = document.getElementById(id);
	var headerHeight = document.getElementsByTagName("nav").item(0).clientHeight;
	// scroll to your element
	node.scrollIntoView(true);

	// scroll down the height of the header
	var scrolledY = window.scrollY;
	if(scrolledY){
	  window.scroll(0, scrolledY - headerHeight);
	}
}

function scrollToTop() {
	window.scroll(0, 0);
}

function getDate(number, timeFormat, dateFormat) {
	//console.log(number);
	number = number.replace(" ", "T");
	
	// parse ISO string
	var date = new Date(number + "+00:00");
	var unix = Date.parse(date);
	
	unix = unix - 60000 * date.getTimezoneOffset();
	date = new Date(unix);
	
	var amPm = false;
	
	if (timeFormat.split("_")[1] == "12") {
		amPm = true;
	}
	
	timeFormat = timeFormat.split("_")[0];
	
	
	var day = date.getUTCDate();
	var month = date.getUTCMonth() + 1;
	var year = date.getFullYear();
	
	day = "" + day;
	month = "" + month;
	year = "" + year;
	
	if (day.length<2) {
		day = "0" + day;
	}
	if (month.length<2) {
		month = "0" + month;
	}
	
	var hours = date.getUTCHours();
	var minutes = date.getUTCMinutes();
	var append = "";
	if (amPm) {
		append = " AM";
		if (hours > 11) {
			hours = hours - 12;
			append = " PM";
		}
		if (hours == 0) {
			hours = 12;
		}
	}
	
	hours = "" + hours;
	minutes = "" + minutes;
	
	if (hours.length<2) {
		hours = "0" + hours;
	}
	if (minutes.length<2) {
		minutes = "0" + minutes;
	}
	
	dateString = dateFormat;
	dateString = dateString.replace("#D", day);
	dateString = dateString.replace("#M", month);
	dateString = dateString.replace("#Y", year);
	
	timeString = timeFormat;
	timeString = timeString.replace("#H", hours);
	timeString = timeString.replace("#M", minutes);
	timeString += append;
	
	//return  dateString + " - " + date.toTimeString().substr(0,5) + " Uhr";
	return  dateString + " - " + timeString;
}


function callLanguage(site) {
	var lang = getUrlVars()["lang"];
	if (lang == null) {
		if (window.location.href.indexOf("?")<0) {
			window.location.href = window.location.href + "?lang=de";
		} else {
			window.location.href = window.location.href + "&lang=de";
		}
	}
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (data) {
		language(site, data, lang);
	});
}

function language(site, data, lang) {
	console.log(data);
	// general
	var html = "";
	for (var i=0; i<data.general.navbar.length; i++) {
		html += '<li><a href="./' + data.general.navbar[i].link + '/?lang=' + lang;
		if (data.general.navbar[i].vars.length>0) {
			html += "&" + data.general.navbar[i].vars;
		}
		html += '">' + data.general.navbar[i].text + '</a></li>';
	}
	//document.getElementById("navbar").innerHTML = html;
	var other = data.general.other;
	html = "";
	for (var i=0; i<data.general.footer.length; i++) {
		html += '<li><a href="./' + data.general.footer[i].link + '/?lang=' + lang;
		if (data.general.footer[i].vars.length>0) {
			html += "&" + data.general.footer[i].vars;
		}
		html += '">' + data.general.footer[i].text + '</a></li>';
	}
	for (var i=0; i<other.length; i++) {
		html += '<li><a href="' + site + '/?lang=' + other[i][0];
		html += '">' + other[i][1] + '</li>';
	}
	document.getElementById("footer").getElementsByTagName("ul").item(0).innerHTML = html;
	var lengthF = document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").length
	//document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").item(lengthF-1).href = site + "/" + "?lang=" + lang;
	document.getElementById("bannerLink").href += "?lang=" + lang;
	
	if (site == "browse") {
		// browse
		var browse = data.browse;
		document.getElementById("label").innerHTML = browse.label;
		document.getElementById("privateListLabel").innerHTML = browse.privateListLabel;
		document.getElementById("searchButton").innerHTML = browse.searchButton;
		document.getElementById("privateSearchButton").innerHTML = browse.privateSearchButton;
		document.getElementById("searchForm").placeholder = browse.searchField;
		document.getElementById("privateSearch").innerHTML = browse.privateSearch;
		//document.getElementById("privateSearchForm").placeholder = browse.privateSearchField;
	} else if (site == "list") {
		// list
		var list = data.list;
		// buttons
		for (var key in list.buttons) {
			document.getElementById(key).innerHTML = eval("list.buttons." + key);
		}
		// labels
		for (var key in list.labels) {
			document.getElementById(key).innerHTML = eval("list.labels." + key);
		}
		// placeholders
		for (var key in list.placeholders) {
			document.getElementById(key).placeholder = eval("list.placeholders." + key);
		}
		// divs
		for (var key in list.divs) {
			document.getElementById(key).innerHTML = eval("list.divs." + key);
		}
		document.getElementById("uploadHelpText").getElementsByTagName("a").item(0).href = "example_" + lang + ".csv";
	} else if (site == "lookup") {
		var lookup = data.lookup;
		for (var key in lookup.divs) {
			document.getElementById(key).innerHTML = eval("lookup.divs." + key);
		}
		var q = getUrlVars()["q"];
		if (q != null && q.length>0) {
			var length = document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").length
			document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").item(length-1).href += "&q=" + q;
		}
		
	} else if (site == "scannedList") {
		var scannedList = data.scannedList;
		for (var key in scannedList.divs) {
			document.getElementById(key).innerHTML = eval("scannedList.divs." + key);
		}
		for (var key in scannedList.buttons) {
			document.getElementById(key).innerHTML = eval("scannedList.buttons." + key);
		}
		for (var key in scannedList.tooltips) {
			document.getElementById(key).title = eval("scannedList.tooltips." + key);
		}
		
		var list = getUrlVars()["list"];
		var group = getUrlVars()["group"];
		var showall = getUrlVars()["showall"];
		if (showall == null || showall.length<1) {
			showall = false;
		}
		var length = document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").length
		document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").item(length-1).href += "&list=" + list +"&group=" + group + "&showall=" + showall;
	} else if (site == "scan") {
		var site = getUrlVars()["site"];
		var scan = getUrlVars()["scan"];
		var length = document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").length
		document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").item(length-1).href += "&site=" + site +"&scan=" + scan;
		for (var key in data.scan.divs) {
			document.getElementById(key).innerHTML = eval("data.scan.divs." + key);
		}
		for (var key in data.scan.buttons) {
			document.getElementById(key).innerHTML = eval("data.scan.buttons." + key);
		}
		var html = '';
		for (var i=0; i<data.scan.https.list.length; i++) {
			html += '<li>' + data.scan.https.list[i] + '<li>';
		}
		document.getElementById("httpsList").innerHTML = html;
	} else if (site == "index") {
		var html = "";
		for (var i=0; i<data.index.leftColumn.length; i++) {
			html += '<div style="margin-bottom:10px;">';
			html += data.index.leftColumn[i];
			html += '</div>';
		}
		document.getElementById("leftColumn").innerHTML = html;
		html = "";
		for (var i=0; i<data.index.testCriteria.length; i++) {
			html += '<li>';
			html += data.index.testCriteria[i];
			html += '</li>';
		}
		document.getElementById("testCriteria").innerHTML = html;
		for (var key in data.index.divs) {
			document.getElementById(key).innerHTML = eval("data.index.divs." + key);
		}
		document.getElementById("searchListButton").href += "?lang=" + lang;
		document.getElementById("createListButton").href += "?lang=" + lang;
		document.getElementById("popularThirdParties").href += "?lang=" + lang;
		
	} else if (site == "thirdParties") {
		for (var key in data.thirdParties.divs) {
			document.getElementById(key).innerHTML = eval("data.thirdParties.divs." + key);
		}
		var list = getUrlVars()["list"];
		var group = getUrlVars()["group"];
		var length = document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").length;
		document.getElementById("footer").getElementsByTagName("ul").item(0).getElementsByTagName("a").item(length-1).href += "&list=" + list + "&group=" + group;
	} else if (site == "login") {
		for (var key in data.login.divs) {
			document.getElementById(key).innerHTML = eval("data.login.divs." + key);
		}
		for (var key in data.login.placeholders) {
			document.getElementById(key).placeholder = eval("data.login.placeholders." + key);
		}
	} else if (site == "user") {
		for (var key in data.user.labels) {
			document.getElementById(key).innerHTML = eval("data.user.labels." + key);
		}
		for (var key in data.user.divs) {
			document.getElementById(key).innerHTML = eval("data.user.divs." + key);
		}
	}
	
	// general: set the login/logout link in header
	var loggedIn = getCookie("login");
	
	if (loggedIn != null && loggedIn == "true") {
		var length = document.getElementById("navbar").getElementsByTagName("a").length;
		var logoutLink = document.getElementById("navbar").getElementsByTagName("a").item(length-1);
		logoutLink.innerHTML = data.general.logout;
		logoutLink.href = "index/?logout=true&lang=" + lang;
	} else {
		var length = document.getElementById("navbar").getElementsByTagName("a").length;
		var userLink = document.getElementById("navbar").getElementsByTagName("a").item(length-2);
		userLink.style.display = "none";
	}
}


function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    //document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    document.cookie = cname + "=" + cvalue + ";path=/";
}

function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}


function init(site) {
	
	// if site is index, check if log out == true
	if (site == "index") {
		logout();
	}
	
  // TODO: use django i18n instead of js translations
	//callLanguage(site);
	//callCookies(site);
}

function callCookies(site) {
	//setCookie("user", "test_username", 5);
	//var username = getCookie("user");
	
	
	if (site != "login") {
		//setCookie("lastPage", document.location.href, 5)
	}
	
	
}
