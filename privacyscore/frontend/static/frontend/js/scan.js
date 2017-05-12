var langData;
var global_diagram_site;

function loadPage() {
	var lang = getUrlVars()["lang"];
	if (lang == null || lang.length<1) {
		lang = "de";
	}
	$.getJSON("/static/frontend/lang/" + lang + ".json", function (data) {
		langData = data;
		
		document.getElementById("loader").style.display = "block";
		// when loading site, check for url variables
		var siteid = getUrlVars()["site"];
		var scanid = getUrlVars()["scan"];
		global_diagram_site = siteid;
		
		$.get(apiUrl + "ShowScan/" + siteid + "/" + scanid, function (jsonString) {
			data = JSON.parse(jsonString);
			console.log(data);
			if (data == null) {			// todo
				document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListFound;
			} else if (data.hasOwnProperty("type") && data.type == "error" && data.message == "This list is private. Please login.") {
				document.getElementsByTagName("content").item(0).innerHTML =  "<br>" + langData.scannedList.alerts.noListPrivate;
				document.getElementsByTagName("content").item(0).style.display = "block";
				document.getElementById("loader").style.display = "none";
			} else {
				callback(data);
			}
		});
	});
}


function callback(json){
	console.log(json);
	
	if (json.scans[0].success) {
		var thatDate = getDate(json.scans[0].starttime, langData.timeFormat, langData.dateFormat);
		//console.log(json.scans[0].starttime);
		setTitle(json.url, thatDate);
		setHeader(json.url, thatDate);
		setFinalUrl(json.scans[0].final_url);
		setOldNewScans(json._id.$oid, json.scans[0].scan_group_id.$oid);
		setBackToListButton(json.list_id.$oid, json.scans[0].scan_group_id.$oid, json.singlesite);
		setDashboard(json.scans[0]);
		//setDashboardFixed();
		setHttps(json.scans[0].https, json.url);
		//setReferrers(json.scans[0].referrer, json.url);
		var cookies = json.scans[0].flashcookies.concat(json.scans[0].profilecookies);
		setCookies(cookies);
		setThirdParties(json.scans[0].third_parties, json.scans[0].third_party_requests, json.url);
		setGeoip(json.scans[0]);
		setHttpHeaders(json.scans[0].headerchecks);
	} else {
		var html = "<h3>";
		html += json.url;
		html += "<br>";
		html += langData.scan.alerts.scanError;
		html += "</h3>";
		document.getElementsByTagName("content").item(0).innerHTML = html;
	}
	
	document.getElementById("loader").style.display = "none";
	document.getElementsByTagName("content").item(0).style.display = "block";
	
}

function setTitle(text, date) {
	document.getElementsByTagName("head").item(0).getElementsByTagName("title").item(0).innerHTML = "PrivacyScore - Ergebnisse für " + text + " - " + date;
}

function setHeader(text, date) {
	document.getElementById("header").getElementsByTagName("span").item(0).innerHTML = text;
	document.getElementById("header").getElementsByTagName("span").item(1).innerHTML = '<span class="glyphicon glyphicon-time"></span>' + date;
}

function setFinalUrl(text) {
	document.getElementById("finalUrl").getElementsByTagName("span").item(0).innerHTML = text;
}

function setBackToListButton(list, group, singlesite) {
	var button = document.getElementById("backToListButton");
	if (singlesite) {
		button.style.display = "none";
	} else {
		button.href = "scannedList.html?lang=" + langData.lang + "&list=" + list + "&group=" + group;
	}
}

function setDashboard(scan) {
	var dashboard = document.getElementById("dashboard");
	
	// set score
	var color = "#000000";
	if (scan.score == "A") {
		color = "#008000";
	} else if (scan.score == "B") {
		color = "#008000";
	} else if (scan.score == "C") {
		color = "#FF7F00";
	} else if (scan.score == "D") {
		color = "#FF7F00";
	} else if (scan.score == "E") {
		color = "#FF0000";
	} else if (scan.score == "F") {
		color = "#FF0000";
	}
	
	dashboard.getElementsByClassName("col-md-2").item(0).getElementsByTagName("div").item(0).style.color = color;
	dashboard.getElementsByClassName("col-md-2").item(0).getElementsByTagName("div").item(0).innerHTML = scan.score;
	dashboard.getElementsByClassName("col-md-2").item(0).getElementsByTagName("div").item(1).innerHTML = langData.scan.dashboard.score;
	
	// set https
	color = "#000000";
	var icon = "unlock-alt";
	var text = "";
	if (scan.https) {
		color = "#008000";
		text = langData.scan.dashboard.https;
		icon = "lock";
	} else {
		color = "#FF0000";
		text = langData.scan.dashboard.noHttps;
	}
	//var html = 
	dashboard.getElementsByClassName("col-md-2").item(1).getElementsByTagName("div").item(0).innerHTML = '<i onclick="scrollToHTTPS();" class="fa fa-' + icon + ' fa-lg" style="color:' + color + '; cursor: pointer;"></i>'
	dashboard.getElementsByClassName("col-md-2").item(1).getElementsByTagName("div").item(1).innerHTML = text;
	
	
	//set referrers
	// color = "#000000";
	// icon = "";
	// text = "";
	// if (!scan.referrer) {
		// color = "#008000";
		// text = "Keine Referer übertragen";
		// icon = '<span onclick="scrollToRef();" class="glyphicon glyphicon-sunglasses" style="color:' + color + '; cursor: pointer;"></span>';
		icon = '<i class="fa fa-umbrella fa-lg" style="color:' + color + '"></i>';
	// } else {
		// color = "#FF0000";
		// text = "Referer übertragen";
		// icon = '<i onclick="scrollToRef();" class="fa fa-tint fa-lg" style="color:' + color + '; cursor: pointer;"></i>';
	// }
	// dashboard.getElementsByClassName("col-md-2").item(2).getElementsByTagName("div").item(0).innerHTML = icon;
	// dashboard.getElementsByClassName("col-md-2").item(2).getElementsByTagName("div").item(1).innerHTML = text;
	
	// set third parties
	dashboard.getElementsByClassName("col-md-2").item(2).getElementsByTagName("div").item(0).innerHTML = "<span onclick='scrollToThirdParty();' style='cursor:pointer;'>" + scan.third_parties_anzahl + " (" + scan.third_party_requests_anzahl + ")</span>";
	dashboard.getElementsByClassName("col-md-2").item(2).getElementsByTagName("div").item(1).innerHTML = langData.scan.dashboard.thirdParty;
	
	// set number of cookies
	var numberOfCookies = scan.cookies_anzahl;
	dashboard.getElementsByClassName("col-md-2").item(3).getElementsByTagName("div").item(0).innerHTML = "<span onclick='scrollToCookies();' style='cursor:pointer;'>" + numberOfCookies + "</span>";
	dashboard.getElementsByClassName("col-md-2").item(3).getElementsByTagName("div").item(1).innerHTML = text = langData.scan.dashboard.cookies;
	
	// set hsts header
	var hsts = false;
	console.log(scan);
	for (var i=0; i<scan.headerchecks.length; i++) {
		if (scan.headerchecks[i].hasOwnProperty("key") && scan.headerchecks[i].key == "hsts" && scan.headerchecks[i].status.toLowerCase() == "ok") {
			hsts = true;
		}
	}
	
	// set hsts header field
	color = "#000000";
	var icon = "unlock-alt";
	var text = "";
	if (hsts) {
		color = "#008000";
		text = langData.scan.dashboard.httpHeader;
		icon = "lock";
	} else {
		color = "#FF0000";
		text = langData.scan.dashboard.httpHeaderNotSet;
	}
	
	// var number = 0;
	// var of = 0;
	// for (var key in scan.http_headers) {
		// of++;
		// if (scan.http_headers[key]) {
			// number++;
		// }
	// }
	dashboard.getElementsByClassName("col-md-2").item(4).getElementsByTagName("div").item(0).innerHTML = '<i onclick="scrollToHeaders();" class="fa fa-' + icon + ' fa-lg" style="color:' + color + '; cursor: pointer;"></i>'
	dashboard.getElementsByClassName("col-md-2").item(4).getElementsByTagName("div").item(1).innerHTML = text;
}

function setDashboardFixed() {
	// TODO?
	document.getElementById("dashboard").style.position = "fixed";
	height = document.getElementById("dashboard").clientHeight;
	document.getElementById("dashboard").style.margin = "50px 10px 20px 30px";
}

function setHttps(https, url) {
	var html = "<h3>";
	var diagramIcon = "";
	diagramIcon = '<i style="margin-left:10px; display:none;" id="showHTTPSDiagram" class="fa fa-line-chart" onclick="openAndLoadDiagram(' + "'" + "httpsDiagram" + "'" + ');"></i>';
	if (https) {
		html += '<i class="fa fa-lock fa-lg" style="color:#008000"></i> '
		html += langData.scan.https.headers.httpsTrue + diagramIcon + "</h3>";
		html += langData.scan.https.headers.httpsTrueStandard.replace("#URL","<b>" + url + "</b> ");
	} else {
		html += '<i class="fa fa-unlock-alt fa-lg" style="color:#FF0000"></i> '
		html += langData.scan.https.headers.httpsFalse + diagramIcon + "</h3>";
		html += langData.scan.https.headers.httpsFalseStandard.replace("#URL","<b>" + url + "</b> ");
	}
	document.getElementById("https").getElementsByTagName("div").item(0).innerHTML = html;
}

function setReferrers(ref, url) {
	var html = "<h3>";
	if (!ref) {
		html += '<span class="glyphicon glyphicon-sunglasses" style="color:#008800"></span> ';
		//html += '<i class="fa fa-umbrella fa-lg" style="color:#008800"></i> ';
		html += "Keine Referer übertragen</h3>";
		html += "<b>" + url + "</b> ...";
	} else {
		html += '<i class="fa fa-tint fa-lg" style="color:#FF0000"></i> '
		html += "Referer an Website übertragen</h3>";
		html += url + " ...";
	}
	document.getElementById("referrers").getElementsByTagName("div").item(0).innerHTML = html;
}

function setCookies(cookies, url) {
	var diagramIcon = "";
	diagramIcon = '<i style="margin-left:10px; display:none;" id="showCookiesDiagram" class="fa fa-line-chart" onclick="openAndLoadDiagram(' + "'" + "cookiesDiagram" + "'" + ');"></i>';
	var html = "<h3>Cookies <small>(" + cookies.length + ")</small>" + diagramIcon + "</h3>";
	if (cookies.length < 1) {
		html += langData.scan.cookies.noCookies;
	} else {
		html += "<table class='table'><thead><tr><th>" + langData.scan.cookies.url + "</th><th>" + langData.scan.cookies.host + "</th><th>" + langData.scan.cookies.name + "</th><th>" + langData.scan.cookies.value + "</th><th>" + langData.scan.cookies.expiry + "</th></tr></thead>";
		html += "<tbody>";
		for (var i=0; i<cookies.length; i++) {
			html += '<tr>';
			html += '<td data-toggle="tooltip" title="' + cookies[i].baseDomain + '">' + cookies[i].baseDomain + '</td>';
			html += '<td data-toggle="tooltip" title="' + cookies[i].host + '">' + cookies[i].host + '</td>';
			html += '<td data-toggle="tooltip" title="' + cookies[i].name + '">' + cookies[i].name + '</td>';
			html += '<td data-toggle="tooltip" title="' + cookies[i].value + '">' + cookies[i].value + '</td>';
			var thisDate = new Date(Date.now() + cookies[i].expiry)
			thisDate = thisDate.toISOString();
			//console.log(thisDate);
			thisDate = thisDate.substring(0,thisDate.length-5);
		//	console.log(thisDate);
			html += '<td data-toggle="tooltip" title="' + getDate(thisDate, langData.timeFormat, langData.dateFormat) + '">' + getDate(thisDate, langData.timeFormat, langData.dateFormat) + '</td>';
			html += '</tr>';
		}
		html += "</tbody></table>";
	}
	document.getElementById("cookies").getElementsByTagName("div").item(0).innerHTML = html;
}

function setThirdParties(thirdParties, thirdPartyRequests, url) {
	var diagramIcon = "";
	diagramIcon = '<i style="margin-left:10px; display:none;" id="showThirdDiagram" class="fa fa-line-chart" onclick="openAndLoadDiagram(' + "'" + "thirdDiagram" + "'" + ');"></i>';
	document.getElementById("thirdPartyRequestsDetails").innerHTML = document.getElementById("thirdPartyRequestsDetails").innerHTML.replace("#URL", "<b>" + url + "</b>");
	var html = "<h3>" + langData.scan.thirdParties.thirdParties + " <small>(" + thirdParties.length + ")</small>" + diagramIcon + "</h3>";
	if (thirdParties.length < 1) {
		html += langData.scan.thirdParties.noThirdParties;
	} else {
		html += "<table class='table'><thead><tr><th>" + langData.scan.thirdParties.url + "</th></thead>";
		html += "<tbody>";
		for (var i=0; i<thirdParties.length; i++) {
			html += '<tr>';
			html += '<td data-toggle="tooltip" title="' + thirdParties[i] + '">' + thirdParties[i] + '</td>';
			html += '</tr>';
		}
		html += "</tbody></table>";
	}
	document.getElementById("third_parties").getElementsByClassName("col-md-6").item(0).innerHTML = html;
	
	diagramIcon = '<i style="margin-left:10px; display:none;" id="showThirdReqDiagram" class="fa fa-line-chart" onclick="openAndLoadDiagram(' + "'" + "thirdReqDiagram" + "'" + ');"></i>';
	html = "<h3>" + langData.scan.thirdParties.thirdPartyRequests + " <small>(" + thirdPartyRequests.length + ")</small>" + diagramIcon + "</h3>";
	if (thirdPartyRequests.length < 1) {
		html += langData.scan.thirdParties.noThirdPartyRequests;
	} else {
		html += "<table class='table'><thead><tr><th>" + langData.scan.thirdParties.url + "</th></thead>";
		html += "<tbody>";
		for (var i=0; i<thirdPartyRequests.length; i++) {
			html += '<tr>';
			html += '<td data-toggle="tooltip" title="' + thirdPartyRequests[i] + '">' + thirdPartyRequests[i] + '</td>';
			html += '</tr>';
		}
		html += "</tbody></table>";
	}
	document.getElementById("third_parties").getElementsByClassName("col-md-6").item(1).innerHTML = html;
}

function setGeoip(scan) {
	var html = "<h3>Geo-IP</h3>";
	
	if (scan.geoip_all_webservers_in_germany) {
		html += "<div>" + langData.scan.geoip.allWebservers + "</div>";
	} else {
		html += "<div>" + langData.scan.geoip.notAllWebservers + "</div>";
	}
	if (scan.domain_has_mailservers) {
		if (scan.geoip_all_mailservers_in_germany) {
			html += "<div>" + langData.scan.geoip.allMailservers + "</div>";
		} else {
			html += "<div>" + langData.scan.geoip.notAllMailservers + "</div>";
		}
	}
	

	if (scan.hasOwnProperty("geoip")) {
		
		
		var geoArray = [];
		
		for (var key in scan.geoip) {
			geoArray.push({"key": scan.geoip[key], "value": key})
		}
		
		console.log(geoArray);

		// sort the array (bubble sort)
		var isSorted = false;
		while (!isSorted) {
			isSorted = true;
			for (var i=0; i<geoArray.length-1; i++) {
				// switch the two array objects if they are in wrong order
				if (geoArray[i].value>geoArray[i+1].value) {
					var temp = geoArray[i];
					geoArray[i] = geoArray[i+1];
					geoArray[i+1] = temp;
					isSorted = false;
				}
			}
		}
		
		html += "<table class='table' style='margin-top:10px;'><thead><tr><th>" + langData.scan.geoip.key + "</th><th>" + langData.scan.geoip.value + "</th></tr></thead>";//<th>" + langData.scan.geoip.details + "</th></tr></thead>";
		html += "<tbody>";
		for (var i=0; i<geoArray.length; i++) {
				html += "<tr><td>" + geoArray[i].value + "</td>";
				html += "<td>" + geoArray[i].key + "</td>";
				//html += "<td>" + "Erklärung" + "</td>";
				html += "</tr>";
		}
		
		
		html += "</tbody></table>";
	}
	document.getElementById("geoip").getElementsByTagName("div").item(0).innerHTML = html;
}

function setHttpHeaders(headers) {
	// readable names for the http headers
	//headerText = ["Content-Security-Policy", "Public-Key-Pins", "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options", "X-Xss-Protection"];
	//headerLinks = ['https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP', 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Public_Key_Pinning', 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security', 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options', 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options', 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection'];
	// explanation texts for the http headers
	// texts = [	"<a href='https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP'>Content Security Policy</a> ist ein Sicherheitskonzept gegen Angriffe wie Cross-Site-Scripting (XSS).",
				// "<a href='https://developer.mozilla.org/en-US/docs/Web/HTTP/Public_Key_Pinning'>Public Key Pinning</a> ist ein Sicherheitsmechanismus, der ein HTTPS-Protokoll vor Man-in-the-Middle-Angriffen schützt.",
				// "<a href='https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security'>Strict Transport Security</a> ist ein Header-Feld, durch das der Server dem Browser mitteilen kann, dass er für diese Domain für eine bestimmte Zeit nur verschlüsselte HTTPS-Verbindungen benutzen soll. Es schützt u.a. vor Downgrade-Attacken und Session-Hijacking.",
				// "<a href='https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options'>X-Content-Type-Options</a> gibt den MIME-Typ der angeforderten Datei an (z.B. text/html oder image/png). Der so übermittelte Typ kann nicht im HTML-Header überschrieben werden.",
				// "<a href='https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options'>x-Frame-Options</a> sagt dem Browser, ob die Seite in einem Frame dargestellt werden darf und bietet so einen Schutz gegen ClickJacking.",
				// "<a href='https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection'>X-XSS-Protection</a> ist ein Header-Feld, das das Laden einer Seite verhindert, wenn ein XSS-Angrff entdeckt wurde. Durch das Content-Security-Policy-Feld ist es in den meisten modernen Browsern unnötig."
			// ];
	// texts = [	"Content Security Policy ist ein Sicherheitskonzept gegen Angriffe wie Cross-Site-Scripting (XSS).",
				// "Public Key Pinning ist ein Sicherheitsmechanismus, der ein HTTPS-Protokoll vor Man-in-the-Middle-Angriffen schützt.",
				// "Strict Transport Security ist ein Header-Feld, durch das der Server dem Browser mitteilen kann, dass er für diese Domain für eine bestimmte Zeit nur verschlüsselte HTTPS-Verbindungen benutzen soll. Es schützt u.a. vor Downgrade-Attacken und Session-Hijacking.",
				// "X-Content-Type-Options gibt den MIME-Typ der angeforderten Datei an (z.B. text/html oder image/png). Der so übermittelte Typ kann nicht im HTML-Header überschrieben werden.",
				// "x-Frame-Options sagt dem Browser, ob die Seite in einem Frame dargestellt werden darf und bietet so einen Schutz gegen ClickJacking.",
				// "X-XSS-Protection ist ein Header-Feld, das das Laden einer Seite verhindert, wenn ein XSS-Angrff entdeckt wurde. Durch das Content-Security-Policy-Feld ist es in den meisten modernen Browsern unnötig."
	// ];
	
	// sort the array (bubble sort)
	var isSorted = false;
	while (!isSorted) {
		isSorted = true;
		for (var i=0; i<headers.length-1; i++) {
			// switch the two array objects if they are in wrong order
			if (headers[i].key>headers[i+1].key) {
				var temp = headers[i];
				headers[i] = headers[i+1];
				headers[i+1] = temp;
				isSorted = false;
			}
		}
	}
	
	var html = "";
	// var notSet = '<div><span class="glyphicon glyphicon-remove" style="color:' + "#FF0000" + '"></span>Nein</div>';
	// var set = '<div><span class="glyphicon glyphicon-ok" style="color:' + "#008800" + '"></span>Ja</div>';
	html += "<table class='table' style='margin-top:10px;'><thead><tr><th>" + langData.scan.httpHeaders.key + "</th><th>" + langData.scan.httpHeaders.status + "</th><th>" + langData.scan.httpHeaders.value + "</th></tr></thead>";
	html += "<tbody>";
	var keyIndex = 0;
	for (var i=0; i<headers.length; i++) {
		var muted = " class='text-muted'"
		if (i==0) {
			muted = "";
		}

		html += "<tr><td" + muted + ">" + headers[i].key + "</td>";
		html += "<td" + muted + ">" + headers[i].status + "</td>";
		html += "<td" + muted + ">" + headers[i].value + "</td></td>";
	}
	html += "</tbody></table>";
	
	document.getElementById("headers").getElementsByTagName("div").item(1).innerHTML = html;
}

function scrollToHTTPS() {
		scrollTo("https");
}

function scrollToRef() {
		scrollTo("referrers");
}

function scrollToCookies() {
		scrollTo("cookies");
}

function scrollToThirdParty() {
		scrollTo("third_parties");
}

function scrollToHeaders() {
		scrollTo("headers");
}

function setOldNewScans(site, group) {
	$.get(apiUrl + "GetScanGroupsBySite/" + site, function (jsonString) {
		//jsonString = jsonString.replace(/'/g, '"');
		data = JSON.parse(jsonString);
		if (data == null) {
			
		} else {
			
			// show the diagram buttons
			if (data.length>1) {
				document.getElementById("showHTTPSDiagram").style.display = "inline";
				document.getElementById("showThirdDiagram").style.display = "inline";
				document.getElementById("showThirdReqDiagram").style.display = "inline";
				document.getElementById("showCookiesDiagram").style.display = "inline";
			}
			
		console.log(data);
		html = '';
		var otherScans = data;
		//console.log(group);
		for (var i=otherScans.length-1; i>=0; i--) {
			if (otherScans[i]._id.$oid == group) {
				html += '<option selected="selected" value="#">';
				html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
				html += '</option>';
			} else {
				html += '<option value="scan.html?site=';
				html += site;
				html += '&scan=';
				html += otherScans[i].scan_id._id.$oid;
				html += '">';
				html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
				html += '</option>';
			}
		}
		document.getElementById("oldNewScans").innerHTML = html;
		}
	});
}

function toggle(button, id) {
	if (document.getElementById(id).style.height == "100%") {
		// hide
		document.getElementById(id).style.maxHeight = "500px";
		document.getElementById(id).style.height = "";
		button.getElementsByTagName("i").item(0).style.display = "inline";
		button.getElementsByTagName("i").item(1).style.display = "none";
		button.getElementsByTagName("small").item(0).style.display = "inline";
		button.getElementsByTagName("small").item(1).style.display = "none";
		scrollTo(id);
	} else {
		// expand
		document.getElementById(id).style.maxHeight = "";
		document.getElementById(id).style.height = "100%";
		button.getElementsByTagName("i").item(1).style.display = "inline";
		button.getElementsByTagName("i").item(0).style.display = "none";
		button.getElementsByTagName("small").item(1).style.display = "inline";
		button.getElementsByTagName("small").item(0).style.display = "none";
	}
}





function fillDiagramSettings(scanJson, otherScans) {
	//document.getElementById("showDiagramBox").style.display = "block";
	// console.log(1);
	// console.log(scanJson);
	// console.log(otherScans);
		
	var div_scandates = document.getElementById("diagram-box-settings-scandate");
	
	var html = "";
	
	for (var i=otherScans.length-1; i>=0; i--) {
		html += '<div class="checkbox">';
		html += '<label><input ';
		if (i > otherScans.length-4) {
			html += 'checked ';
		}
		html += 'type="checkbox" ';
		html += 'id="group-' + i + '" ';
		html += 'value="';
		html += otherScans[i]._id.$oid;
		html +='">';
		html += getDate(otherScans[i].startdate, langData.timeFormat, langData.dateFormat);
		html += '</label>';
		html += '</div>';
	}
	
	div_scandates.innerHTML = html;
	
	
	
}

function closeDiagram() {
	document.getElementById("diagram-box").style.display = "none";
	//document.getElementById("overlay").style.display = "none";
}

function openDiagram() {
	document.getElementById("diagram-box").style.display = "block";
	$('.collapse').collapse("show")
	//document.getElementById("overlay").style.display = "block";
}

function submitDiagram() {
	var groupsLength = document.getElementById("diagram-box-settings-scandate").getElementsByClassName("checkbox").length;

	var selectedGroups = 0;
	for (var i=0; i<groupsLength; i++) {
		var id = "group-" + i;
		if (document.getElementById(id).checked) {
			selectedGroups++;
		}
	}
	
	// var max = 5;
	// if (selectedGroups>max) {
		// alert("Bitte wählen Sie maximal " + max + " Scans aus!");
	// } else if (selectedGroups<2) {
		// alert("Bitte wählen Sie mindestens zwei Scans aus!");
	// } else {
		// document.getElementById("diagram").innerHTML = "";
		// loadDiagram();
		// $('.collapse').collapse("toggle")
	// }
	
	document.getElementById("diagram").innerHTML = "";
	loadDiagram();
	
}

function openAndLoadDiagram(criterionName) {
	console.log(criterionName);
	document.getElementById(criterionName).checked = true
	document.getElementById("diagramHeader1").innerHTML =  eval("langData.scan.diagramHeaderLabels." + criterionName + "Label") + " ";
	openDiagram();
	document.getElementById("diagram").innerHTML = "";
	loadDiagram(global_diagram_site);
	scrollToTop();
	$('.collapse').collapse("hide");
}