var langData;

function loadPage() {
	var q = getUrlVars()["q"];
	var lang = getUrlVars()["lang"];
	if (lang == null) {
		lang = "de";
	}
	$.get(apiUrl + "LookupScan?searchtext=" + q, function (jsonString) {
		$.getJSON("/static/frontend//static/frontend/lang/" + lang + ".json", function (data) {
			langData = data;
			console.log(jsonString);
			var data = JSON.parse(jsonString);
			console.log(data);
			callback(data);
		});
	});
}

function callback(data) {
	
	if (data.hasOwnProperty("lastList") && data.lastList.hasOwnProperty("singlesite") && data.lastList.singlesite == false) {
		// case: page found in normal list (3)
		callbackNormalList(data);
	} else if (data.hasOwnProperty("lastList") && data.lastList.hasOwnProperty("singlesite") && data.lastList.singlesite == true) {
		// case: page found in singlesite (2)
		callbackSingleList(data);
	} else {
		// case: nothing found for site (1)
		callbackNotFound();
	}
	document.getElementsByTagName("content").item(0).style.display = "block";
}

function callbackSingleList(data) {
	callbackFound(data);
	document.getElementById("lastScanned").style.display = "block";
	document.getElementById("lastScan").style.display = "block";
	document.getElementById("scanSingleSiteListButton").style.display = "inline";
	document.getElementById("scanSingleSiteListButton").value = data.lastList._id.$oid;
}

function callbackNormalList(data){
	callbackFound(data);
	document.getElementById("lastScanned").style.display = "block";
	document.getElementById("lastScan").style.display = "block";
	document.getElementById("lastList").style.display = "block";
	document.getElementById("lastList").style.display = "block";
	document.getElementById("scanNormalListButton").style.display = "inline";
	document.getElementById("scanNormalListButton").value = data.url;
}

function callbackNotFound() {
	var q = getUrlVars()["q"];
	var url = q.replace(/%2F/g, '\/');
	url = url.replace(/%3A/g, ':');
	setHeader(url);
	
	document.getElementById("div_notFound").getElementsByTagName("span").item(0).innerHTML = url;
	document.getElementById("div_notFound").style.display = "block";
	document.getElementById("scanNewButton").value = url;
	document.getElementById("scanNewButton").style.display = "inline";	
}

function callbackFound(data) {
	setHeader(data.url);
	var div = document.getElementById("div_foundInNormalList");
	var date = getDate(data.lastScan.starttime, langData.timeFormat, langData.dateFormat);
	//	date = date.replace("-", "um");
	date += ".";
	document.getElementById("lastScanned").getElementsByTagName("span").item(0).innerHTML = data.url;
	document.getElementById("lastScanned").getElementsByTagName("span").item(1).innerHTML = date;
	
	var html = '<h4>';
	html += ' <a href="scannedList.html?list=';
	html += data.lastList._id.$oid;
	html += "&group=";
	html += data.lastGroup._id.$oid;
	html += '">';
	html += data.lastList.name;
	html += ' <i class="fa fa-arrow-circle-o-right"></i></a></h4>'
	html += '<div>';
	html += '<span class="glyphicon glyphicon-info-sign" data-toggle="tooltip" title=""></span> '
	html += data.lastList.description;
	html += '</div>';
	html += '<div style="margin-top:10px">';
	html += '<span class="glyphicon glyphicon-tags" data-toggle="tooltip" title=""></span> ';
	html += data.lastList.tags.toString().replace(/,/g,", ");
	html += '</div>';
	
	document.getElementById("lastList").getElementsByTagName("li").item(0).innerHTML = html;
	
	html = "<h4>";
	html += ' <a href="scan.html?site=';
	html += data._id.$oid;
	html += "&scan=";
	html += data.lastScan._id.$oid;
	html += '">';
	html += data.url;
	html += ' <i class="fa fa-arrow-circle-o-right"></i></a></h4>'
			
	
	document.getElementById("lastScan").getElementsByTagName("li").item(0).innerHTML = html;
}

function setHeader(url) {
	document.getElementById("header").getElementsByTagName("span").item(0).innerHTML = url;
	document.getElementById("header").style.display = "block";
}


function createSingleList(url) {
	url = url.replace(/%2F/g, '\/');
	url = url.replace(/%3A/g, ':');
	console.log(url);
	
	$.ajax({
            url: apiUrl + '/SingleSite',
            type: 'POST',
			xhrFields: {
				withCredentials: true
			},
            data: {'url': url},
            success: function (jsonString) {
				console.log(jsonString);
				var data = JSON.parse(jsonString);
				progress(data.list_id, data.scan_group_id);
				
            }
        });
}

function scanList(id) {
	
	var req = {"listid": id};
	$.ajax({
		url: apiUrl + '/ScanList',
		type: 'POST',
		data: JSON.stringify(req),
		xhrFields: {
				withCredentials: true
			},
		headers: {
			//'Content-Type': 'application/json; charset=utf-8;'
		},
		success: function (jsonString) {
			console.log(jsonString);
			var data = JSON.parse(jsonString);
			console.log(data);
			progress(id, "");
		}
	});
}

function progress(list_id, scan_group_id) {
	document.getElementById("loader").style.display = "block";
	$.get(apiUrl + "GetScanGroupsByList/" + list_id, function (jsonString) {
		console.log(jsonString);
		data = JSON.parse(jsonString);
		console.log(data);
		
		if (scan_group_id == null || scan_group_id.length<1) {
			scan_group_id = data[data.length-1]._id.$oid
		}
		
		if (data.length<1) {
			setTimeout(function(){progress(list_id, scan_group_id)}, 5000);
		} else {
			for (var i=0; i<data.length; i++) {
				if (data[i]._id.$oid == scan_group_id) {
					if (data[i].state == "finish") {
						// go to scan.html
						goToScan(list_id, scan_group_id)
					} else if (data[i].state == "scanning") {
						// show progress
						//[{"startdate": "2017-03-06T09:48:09.664228", "progress_timestamp_absolute": "2017-03-06T09:50:32.668560", "enddate": "", "progress_timestamp": "42 seconds elapsed", "state": "scanning", "list_id": {"$oid": "58bd2249137ed606ed4effcd"}, "progress": "Analyzing URL 1/1 with test testsslmx (1/3)", "_id": {"$oid": "58bd2249137ed606ed4effcf"}}]
						var html = langData.lookup.progress.scanning;
						html += "<br>" + data[i].progress;
						html += "<br>" + data[i].progress_timestamp;
						document.getElementById("loadingProgress").innerHTML = html;
						// refresh after 5 seconds
						setTimeout(function(){progress(list_id, scan_group_id)}, 5000);
					} else if (data[i].state == "scanning") { 
					
					} else {
						// refresh after 5 seconds
						document.getElementById("loadingProgress").innerHTML = langData.lookup.progress.startScan;
						setTimeout(function(){progress(list_id, scan_group_id)}, 5000);
					}
				}
			}
		}
		// if (data.length>0 && data[data.length-1].hasOwnProperty("_id") && data[data.length-1].state == "scanning") {
			// TODO: 
			// window.location.href = "scannedList.html?list=" + listid + "&group=" + group;
		// } else {
			// refresh after 5 seconds
			// if (data.length>0 && data[data.length-1].hasOwnProperty("progress") && data[data.length-1].hasOwnProperty("progress_timestamp")) {
				// var html = "<br>..." + data[data.length-1].progress;
				// html += "<br>" + data[data.length-1].progress_timestamp;
				// document.getElementById("loadingProgress").innerHTML = html;
			// }
			// setTimeout(function(){progress(list_id, scan_group_id)}, 5000);
		// }
	});
}

function goToScan(list_id, scan_group_id) {
	$.get(apiUrl + "ShowScannedList/" + list_id + "/" + scan_group_id, function (jsonString) {
			data = JSON.parse(jsonString);
			console.log(data);
			if (data != null) {
				var site_id = data.seiten[0]._id.$oid;
				var scan_id = data.seiten[0].scans[0]._id.$oid;
				window.location.href = "scan.html?site=" + site_id + "&scan=" + scan_id;
			}
    });
}
