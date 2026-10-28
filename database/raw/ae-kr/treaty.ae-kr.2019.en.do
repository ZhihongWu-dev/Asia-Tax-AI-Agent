<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="ko" xml:lang="ko">
 <head> 
  <meta http-equiv="X-UA-Compatible" content="IE=edge" /> 
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />    
  <!-- 레이아웃 관련 CSS -->      
  <!-- 레이아웃 관련 CSS //--> 
  <script type="text/javascript" src="/LSW/js/jquery/jquery.min.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/common/common.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/common/drag_search.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/common/CookieUtil.js"></script> 
  <script type="text/javascript" src="/LSW/js/jquery/jquery.loadmask.min.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/common/jquery-custom.js?Time=1793025598"></script> 
  <!-- 레이아웃 관련 JS --> 
  <script type="text/javascript" src="/LSW/js/jquery/jquery-ui.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/jquery/jquery-ui_2017.min.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/jquery/jquery.layout-latest.min.js?Time=1793025598"></script> 
  <script type="text/javascript" src="/LSW/js/common/layout.js?Time=1793025598"></script> 
  <!-- 레이아웃 관련 JS //-->  
  <script type="text/javascript">
        var webRoot = '/LSW';
    </script> 
  <link rel="shortcut icon" type="text/css" href="/LSW/images/ico_favorites.ico" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/lsw/common.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/js/jquery/jquery.loadmask.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/js/jquery/layout-default-latest.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/lsw/layout.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/lsw/board.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/ui_2017.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/fonts.css?Time=1793025598" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/lsw/ext_all_ex.css" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/lsw/common-ex.css" />
  <link rel="stylesheet" type="text/css" href="/LSW/css/lsw/xtheme-layer.css" />
  <style type="text/css">
        .ui-layout-pane {
            padding: 0;
            background:	#EEE;
        }
        .ui-layout-west {
            background:	#CFC;
        }
        .ui-layout-center {
            background:	#FFC;
            padding:	0; /* IMPORTANT - remove padding so pane can 'collapse' to 0-width */
        }

        .ui-layout-west > .ui-layout-center {
            background:	#CFC;
        }

        .ui-layout-west > .ui-layout-south {
            background:	#AFE;
        }
        .ui-layout-pane { border-width: 0; }
        .ui-layout-north { border-bottom-width:	1px; }
        .ui-layout-south { border-top-width: 1px; }
        .ui-layout-resizer-west {
            border-width: 0;
            border-left: 2px solid #b4b4b4;
            background-color:white;
        }
        .ui-layout-toggler {
            border: 0;
            background-color:#fff
        }
        .ui-layout-toggler-west-closed {
            background-image: url("./images/button/leslidev7_2.gif");
            background-color:white;
            background-repeat: no-repeat;
        }
        .ui-layout-toggler-west-open {
            background-image: url("./images/button/leslidev7_1.gif");
            background-color:white;
            background-repeat: no-repeat;
        }
    </style>
  <title>양자조약 &gt; 본문 | 국가법령정보센터</title>
 </head> 
 <body class="popbg2" id="bodyId">        
  <script type="text/javascript" src="/LSW/js/common/common.js"></script> 
  <script type="text/javascript" src="/LSW/js/trty/trtyBInfoP.js"></script> 
  <script type="text/javascript" src="/LSW/js/common/CookieUtil.js"></script> 
  <script type="text/javascript" src="/LSW/js/common/drag_search.js"></script> 
  <script type="text/javascript" src="/LSW/js/common/autocom.js"></script> 
  <script type="text/javascript" src="/LSW/js/common/common-ex.js"></script> 
  <script type="text/javascript">
        //<![CDATA[
        window.onload = function(){
            setDetailSelectCookie('010109', $('#trtySeq').val());
        };

        //본분 인쇄
        function f_InfoPrint(){
            var lang = el('chrClsCd').value;
            if(trtyLangType != ''){
                lang = trtyLangType;
            }
            var param = {trtySeq:el('trtySeq').value, chrClsCd:lang, print:el('print').value};
            var popUrl = "trtyBInfoR.do?" + makeParam(param);
            //openPop(popUrl);
            var win = window.open(popUrl,'', 'scrollbars=yes,toolbar=no,resizable=yes,status=no,menubar=no,width=' + 1000 + ',height=' +  700);
            return false;
        }

        // 즐겨찾기
        function bookmark(){
            var title = el("trtyNm").value;
            var No = el("trtyNo").value;
            var gourl = "http://" + location.host + "/조약/" + Space_All(title)+"/("+Space_All(No)+")";
            lawBookmark(title, gourl);
        }
        //]]>
    </script>   
  <input type="hidden" name="trtySeq" id="trtySeq" value="14055" /> 
  <input type="hidden" name=" " id="chrClsCd" value="010203" /> 
  <input type="hidden" name="print" id="print" value="print" /> 
  <h1 style="display:none;">양자조약 팝업</h1> 
  <hr /> 
  <!-- 스킵 네비게이션 --> 
  <div id="skipnavi"> 
   <p><a href="#trtyInfoDiv">본문 바로가기</a></p> 
  </div> 
  <!-- 스킵 네비게이션 --> 
  <!-- head --> 
  <div class="pophead"> 
   <h2>양자조약</h2> 
   <p><img src="/LSW/images/common/poplogo.gif" alt="법제처 국가법령정보센터" /></p> 
  </div> 
  <!-- head //--> 
  <!-- container --> 
  <div class="body_top_area"> 
   <!-- 좌측 박스 --> 
   <div class="l_bx"> 
    <a class="btn type7" id="ko1_A" title="팝업으로 이동" href="#" onclick="showSndLang('010202');return false;">국문</a> 
    <a class="btn type7 inac" id="en1_A" title="팝업으로 이동" href="#" onclick="showSndLang('010203');return false;">영문</a> 
    <a class="btn type8" id="trtyAttFlListView" href="#" onmouseover="javascript:trtyAttFlListView(this,'');return false;" onmouseout="javascript:trtyAttFlListClose();return false;" onclick="javascript:trtyAttFlListView(this,'');return false;">첨부파일</a> 
   </div> 
   <!-- 좌측 박스 //--> 
   <!-- 우측 박스 --> 
   <div class="r_bx"> 
    <a href="#AJAX" onclick="javascript:goLsTrm();return false;"><img src="/LSW/images/button/btn_lstrm.gif" alt="법령용어" /></a> 
    <a href="#AJAX" id="lsSeHstView" onclick="SaveWindow.showBydSearch(this,270,0);return false;"><img src="/LSW/images/common/btn_v13fn1.gif" alt="화면내검색" /></a> 
    <a href="#AJAX" title="즐겨찾기" onclick="bookmark();"><img src="/LSW/images/common/btn_v13fn8.gif" alt="즐겨찾기" /></a> 
    <a href="#AJAX" title="저장" onclick="javascript:f_InfoSave(this);return false;"><img src="/LSW/images/common/btn_v13fn6.gif" alt="저장" /></a> 
    <a href="#AJAX" onclick="f_InfoPrint();return false;" title="인쇄(팝업으로 이동)"><img src="/LSW/images/common/btn_v13fn7.gif" alt="인쇄" /></a> 
   </div> 
   <!-- 우측 박스 --> 
  </div> 
  <div id="trtyInfoDiv">     
   <input type="hidden" name="trtySeq" id="trtySeq" value="14055" /> 
   <input type="hidden" name="trtyNm" id="trtyNm" value="대한민국과 아랍에미리트연합국 간의 소득에 대한 조세의 이중과세 방지와 탈세 및 조세회피의 예방을 위한 협약" /> 
   <input type="hidden" name="trtyNo" id="trtyNo" value="2455" /> 
   <div class="tbl6" id="tbl6Id"> 
    <table cellpadding="0" cellspacing="0" summary="양자조약 검색결과 상세화면으로 항목은 체결대상국가, 분야, 가.국문, 나.영문, 관보게재일, 발효일 입니다"> 
     <caption>
      양자조약 검색결과 상세화면
     </caption> 
     <colgroup>
      <col width="13%" />
      <col width="27%" />
      <col width="13%" />
      <col width="47%" />
     </colgroup> 
     <tbody> 
      <tr> 
       <th scope="row" class="ctne2">체결대상국가</th> 
       <td colspan="3">U.A.E 아랍에미리트</td> 
      </tr> 
      <tr> 
       <th scope="row" class="ctne2">분야</th> 
       <td colspan="3">조세</td> 
      </tr> 
      <tr> 
       <th scope="row" colspan="4" class="ctne1">[ 조약명 ]</th> 
      </tr> 
      <tr> 
       <th scope="row">가.국문</th> 
       <td colspan="3" class="ctne2">대한민국과 아랍에미리트연합국 간의 소득에 대한 조세의 이중과세 방지와 탈세 및 조세회피의 예방을 위한 협약</td> 
      </tr> 
      <tr> 
       <th scope="row">나.영문</th> 
       <td colspan="3">CONVENTION BETWEEN THE REPUBLIC OF KOREA AND THE UNITED ARAB EMIRATES FOR THE ELIMINATION OF DOUBLE TAXATION WITH RESPECT TO TAXES ON INCOME AND THE PREVENTION OF TAX EVASION AND AVOIDANCE</td> 
      </tr> 
      <tr> 
       <th scope="row" class="ctne2">관보게재일</th> 
       <td>2020년 02월 24일</td> 
       <th scope="row" class="ctne2">발효일</th> 
       <td>2020년 02월 29일 (조약 제2455 호)</td> 
      </tr> 
      <!--
			<tr>
				<th scope="row">첨부파일</th>
				<td colspan="3" class="ctne2">
					<a href="flDownload.do?flSeq=162172145" target="_self"><img src="/LSW/images/button/btn_han.gif" alt="다운로드" align="absmiddle" />&nbsp;⊙조약 제2455호 대한민국과 아랍에미리트연합국 간의 소득에 대한 조세의 이중과세 방지와 탈세 및 조세회피의 예방을 위한 협약.hwp</a><br/>
					
				</td>
			</tr> --> 
      <tr> 
       <td colspan="4" class="ctne1"> CONVENTION BETWEEN THE REPUBLIC OF KOREA AND THE UNITED ARAB EMIRATES FOR THE ELIMINATION OF DOUBLE TAXATION WITH RESPECT TO TAXES ON INCOME AND THE PREVENTION OF TAX EVASION AND AVOIDANCE <br /> <br />The Republic of Korea and the United Arab Emirates , <br /> <br /> Desiring to further develop their economic relationship and to enhance their cooperation in tax matters, <br /> <br /> Intending to conclude a Convention for the elimination of double taxation with respect to taxes on income without creating opportunities for non-taxation or reduced taxation through tax evasion or avoidance(including through treaty-shopping arrangements aimed at obtaining reliefs provided in this Convention for the indirect benefit of residents of third States), <br /> <br /> Have agreed as follows: <br /> <br /> <br />Article 1 PERSONS COVERED <br /> <br /> This Convention shall apply to persons who are residents of one or both of the Contracting States. <br /> <br /> <br />Article 2 TAXES COVERED <br /> <br />1. This Convention shall apply to taxes on income imposed on behalf of a Contracting State or of its political subdivisions or local authorities, irrespective of the manner in which they are levied. <br /> <br />2. There shall be regarded as taxes on income all taxes imposed on total income, or on elements of income, including taxes on gains from the alienation of movable or immovable property, taxes on the total amounts of wages or salaries paid by enterprises. <br /> <br />3. The existing taxes to which the Convention shall apply are in particular: <br /> a) in the case of the Republic of Korea: <br /> (i) the income tax; <br /> (ii) the corporation tax; <br /> (iii) the special tax for rural development, and <br /> (iv) the local income tax; <br /> (hereinafter referred to as "Korean tax") <br /> b) in the case of the United Arab Emirates: <br /> (i) the income tax; and <br /> (ii) the corporation tax; <br /> (hereinafter referred to as "the United Arab Emirates tax") <br /> <br />4. The Convention shall apply also to any identical or substantially similar taxes that are imposed after the date of signature of the Convention in addition to, or in place of, the existing taxes. The competent authorities of the Contracting States shall notify each other of any significant changes that have been made in their taxation laws. <br /> <br /> <br />Article 3 GENERAL DEFINITIONS <br /> <br />1. For the purposes of this Convention, unless the context otherwise requires: <br /> a) the term "Korea" means the Republic of Korea, and when used in a geographical sense, the territory of the Republic of Korea including its territorial sea, and any area adjacent to the territorial sea of the Republic of Korea which, in accordance with international law, has been or may hereafter be designated under the laws of the Republic of Korea as an area within which the sovereign rights or jurisdiction of the Republic of Korea with respect to the sea-bed and sub-soil, and their natural resources may be exercised; <br /> b) the term "the United Arab Emirates" means the United Arab Emirates and when used in a geographical sense, means the area in which the territory is under sovereignty as well as the territorial sea, airspace and submarine areas over which the United Arab Emirates exercise sovereign rights, including the mainland and islands under its jurisdiction in respect of any activity carried on in connection with the exploration for or the exploitation of natural resources; <br /> c) the terms "a Contracting State" and "the other Contracting State" mean Korea or the United Arab Emirates, as the context requires; <br /> d) the term "enterprise" applies to the carrying on of any business; <br /> e) the term "tax" means Korean tax or the United Arab Emirates tax, as the context requires; <br /> f) the term "person" includes an individual, a company and any other body of persons; <br /> g) the term "company" means any body corporate or any entity that is treated as a body corporate for tax purposes; <br /> h) the terms "enterprise of a Contracting State" and "enterprise of the other Contracting State" mean respectively an enterprise carried on by a resident of a Contracting State and an enterprise carried on by a resident of the other Contracting State; <br /> i) the term "international traffic" means any transport by a ship or aircraft operated by an enterprise of a Contracting State, except when the ship or aircraft is operated solely between places in the other Contracting State; <br /> j) the term "national", in relation to a Contracting State, means: <br /> (i) any individual possessing the nationality of that Contracting State; and <br /> (ii) any legal person, partnership, association deriving its status as such from the laws in force in that Contracting State; <br /> k) the term "business" includes the performance of professional services and of other activities of an independent character. <br /> l) the term "competent authority" means: <br /> (i) in the case of the Republic of Korea, the Minister of Economy and Finance or the Minister’s authorised representative; <br /> (ii) in the case of the United Arab Emirates, the Minister of Finance or the Minister’s authorised representative; <br /> <br />2. As regards the application of the Convention at any time by a Contracting State, any term not defined therein shall, unless the context otherwise requires, have the meaning that it has at that time under the law of that Contracting State for the purposes of the taxes to which the Convention applies, any meaning under the applicable tax laws of that Contracting State prevailing over a meaning given to the term under other laws of that Contracting State. <br /> <br /> <br />Article 4 RESIDENT <br /> <br />1. For the purposes of this Convention, the term "resident of a Contracting State" means: <br /> a) in the case of the Republic of Korea: <br /> any person who, under the laws of that State, is liable to tax therein by reason of that person’s domicile, residence, place of head or main office, place of management or any other criterion of a similar nature, and also includes that State and any political subdivision or local authority thereof. This term, however, does not include any person who is liable to tax in that State in respect only of income from sources in that State. <br /> b) in the case of the United Arab Emirates: <br /> an individual who under the laws of the United Arab Emirates is a national of the United Arab Emirates who has that person’s domicile or residence therein and any other individual who is domiciled in the United Arab Emirates and a company or any financial institution which is incorporated in the United Arab Emirates, and has its place of effective management therein. <br /> <br />2. For the purposes of paragraph 1, a resident of a Contracting State shall include: <br /> a) the Government of that Contracting State and any political subdivision or local Government authority thereof; <br /> b) any other governmental institution created in that Contracting State under public law such as a corporation, fund, and any other entity the capital of which has its place of effective management therein and is wholly or partially directly or indirectly owned by the federal or local Governments of the United Arab Emirates, including a political subdivision and local authority thereof listed in the Protocol to this Convention; <br /> c) any other entity which has its place of effective management therein and is established in that Contracting State by the Government of that Contracting State or any political subdivision or local Government authority thereof, or any governmental institution as defined in subparagraph b). <br /> <br />3. Where by reason of the provisions of paragraph 1 an individual is a resident of both Contracting States, then the individual’s status shall be determined as follows: <br /> a) the individual shall be deemed to be a resident only of the Contracting State in which the individual has a permanent home available to the individual; if the individual has a permanent home available to the individual in both Contracting States, the individual shall be deemed to be a resident only of the Contracting State with which the individual’s personal and economic relations are closer (centre of vital interests); <br /> b) if the Contracting State in which the individual has the individual’s centre of vital interests cannot be determined, or if the individual has not a permanent home available to the individual in either Contracting State, the individual shall be deemed to be a resident only of the State in which the individual has an habitual abode; <br /> c) if the individual has an habitual abode in both Contracting States or in neither of them, the individual shall be deemed to be a resident only of the Contracting State of which the individual is a national; <br /> d) if the individual is a national of both States or of neither of them the competent authorities of the Contracting States shall settle the question by mutual agreement. <br /> <br />4. Where by reason of the provisions of paragraph 1 a person other than an individual is a resident of both Contracting States, then it shall be deemed to be a <br />resident only of the Contracting State in which its place of effective management is situated. <br /> <br /> <br />Article 5 PERMANENT ESTABLISHMENT <br /> <br />1. For the purposes of this Convention, the term "permanent establishment" means a fixed place of business through which the business of an enterprise is wholly or partly carried on. <br /> <br />2. The term "permanent establishment" includes especially: <br /> a) a place of management; <br /> b) a branch; <br /> c) an office; <br /> d) a factory; <br /> e) a workshop; and <br /> f) a mine, an oil or gas well, a quarry or any other place relating to extraction of natural resources. <br /> <br />3. A building site, a construction, assembly or installation project or supervisory activities in connection therewith carried out in a Contracting State, constitutes a permanent establishment only if such site, project or activities continue for a period of more than twelve months. <br /> <br />4. The furnishing of services, including consultancy or managerial services, by an enterprise of a Contracting State through employees or other personnel engaged by the enterprise for such purpose, in the other Contracting State constitutes a permanent establishment only if activities of that nature continue for a period or periods aggregating more than twelve months. <br /> <br />5. Notwithstanding the preceding provisions of this Article, the term "permanent establishment" shall be deemed not to include: <br /> a) the use of facilities solely for the purpose of storage, display or delivery of goods or merchandise belonging to the enterprise; <br /> b) the maintenance of a stock of goods or merchandise belonging to the enterprise solely for the purpose of storage, display or delivery; <br /> c) the maintenance of a stock of goods or merchandise belonging to the enterprise solely for the purpose of processing by another enterprise; <br /> d) the maintenance of a fixed place of business solely for the purpose of purchasing goods or merchandise or of collecting information, for the enterprise; <br /> e) the maintenance of a fixed place of business solely for the purpose of carrying on, for the enterprise, any other activity of a preparatory or auxiliary character; <br /> f) the maintenance of a fixed place of business solely for any combination of activities mentioned in subparagraphs a) to e), provided that the overall activity of the fixed place of business resulting from this combination is of a preparatory or auxiliary character. <br /> <br />6. Notwithstanding the provisions of paragraphs 1 and 2, where a person - other than an agent of an independent status to whom paragraph 8 applies - is acting in a Contracting State on behalf of an enterprise of the other Contracting State, that enterprise shall be deemed to have a permanent establishment in the first-mentioned Contracting State in respect of any activities which that person undertakes for the enterprise, if such a person: <br /> a) has and habitually exercises in the first-mentioned Contracting State a general authority to negotiate and conclude contracts for or on behalf of such enterprise; or <br /> b) maintains in the first-mentioned Contracting State a stock of goods or merchandise from which he regularly delivers goods or merchandise on behalf of such enterprise. <br /> <br />7. Notwithstanding the preceding provisions of this Article, an insurance enterprise of a Contracting State shall, except in regard to re-insurance, be deemed to have a permanent establishment in the other Contracting State if it collects premiums in the territory of that other State or insures risks situated therein through a person other than an agent of an independent status to whom paragraph 9 applies. <br /> <br />8. An enterprise of a Contracting State shall not be deemed to have a permanent establishment in the other Contracting State merely because it carries on business in that other Contracting State through a broker, general commission agent or any other agent of an independent status, provided that such persons are acting in the ordinary course of their business. However, when the activities of such an agent are devoted wholly or almost wholly on behalf of that enterprise and other enterprises, which are controlled by it or have a controlling interest in it, he will not be considered an agent of an independent status within the meaning of this paragraph. <br /> <br />9. The fact that a company which is a resident of a Contracting State controls or is controlled by a company which is a resident of the other Contracting State, or which carries on business in that other State (whether through a permanent establishment or otherwise), shall not of itself constitute either company a permanent establishment of the other Contracting State. <br /> <br /> <br />Article 6 INCOME FROM IMMOVABLE PROPERTY <br /> <br />1. Income derived by a resident of a Contracting State from immovable property (including income from agriculture or forestry) situated in the other Contracting State may be taxed in that other Contracting State. <br /> <br />2. The term "immovable property" shall have the meaning which it has under the law of the Contracting State in which the property in question is situated. The term shall in any case include property accessory to immovable property, livestock and equipment used in agriculture and forestry, rights to which the provisions of general law respecting landed property apply, usufruct of immovable property and rights to variable or fixed payments as consideration for the working of, or the right to work, mineral deposits, sources and other natural resources; ships and aircraft shall not be regarded as immovable property. <br /> <br />3. The provisions of paragraph 1 shall apply to income derived from the direct use, letting, or use in any other form of immovable property. <br /> <br />4. The provisions of paragraphs 1 and 3 shall also apply to the income from immovable property of an enterprise. <br /> <br /> <br />Article 7 BUSINESS PROFITS <br /> <br />1. The profits of an enterprise of a Contracting State shall be taxable only in that Contracting State unless the enterprise carries on business in the other Contracting State through a permanent establishment situated in that other Contracting State. If the enterprise carries on business as in that manner, the profits of the enterprise may be taxed in the other State but only so much of them as is attributable to that permanent establishment. <br /> <br />2. Subject to the provisions of paragraph 3, where an enterprise of a Contracting State carries on business in the other Contracting State through a permanent establishment situated therein, there shall in each Contracting State be attributed to that permanent establishment the profits which it might be expected to make if it were a distinct and separate enterprise engaged in the same or similar activities under the same or similar conditions and dealing wholly independently with the enterprise of which it is a permanent establishment. <br /> <br />3. In determining the profits of a permanent establishment, there shall be allowed as deductions those deductible expenses which are incurred for the purposes of the permanent establishment, including executive and general administrative expenses so incurred, whether in the Contracting State in which the permanent establishment is situated or elsewhere, taking into consideration any applicable law or regulations in the concerned Contracting State. However, no such deduction shall be allowed in respect of amounts, if any, paid (otherwise than towards reimbursement of actual expenses) by the permanent establishment to the head office of the enterprise or any of its other offices, by way of royalties, fees or other similar payments in return for the use of patents or other rights, or by way of commission, for specific services performed or for management, or except in the case of a banking enterprise, by way of interest on moneys lent to the head office of the enterprise or any of its other offices. <br /> <br />4. No profits shall be attributed to a permanent establishment by reason of the mere purchase by that permanent establishment of goods or merchandise for the enterprise. <br /> <br />5. Insofar as it has been customary in a Contracting State to determine the profits to be attributed to a permanent establishment on the basis of an apportionment of the total profits of the enterprise to its various parts, nothing in paragraph 2 shall preclude that Contracting State from determining the profits to be taxed by such an apportionment as may be customary; the method of apportionment adopted shall, however, be such that the result shall be in accordance with the principles contained in this Article. <br /> <br />6. For the purposes of the preceding paragraphs, the profits to be attributed to the permanent establishment shall be determined by the same method year by year unless there is good and sufficient reason to the contrary. <br /> <br />7. Where profits include items of income which are dealt with separately in other Articles of this Convention, then the provisions of those Articles shall not be affected by the provisions of this Article. <br /> <br /> <br />Article 8 SHIPPING AND AIR TRANSPORT <br /> <br />1. Profits from the operation of ships or aircraft in international traffic carried on by an enterprise of a Contracting State shall be taxable only in that Contracting State. <br /> <br />2. The provisions of paragraph 1 shall also apply to profits from the participation in a pool, a joint business or an international operating agency. <br /> <br />3. For the purposes of this Article, the terms "profits from the operation of ships or aircraft in international traffic" shall include profits from: <br /> a) the rental of a ship or aircraft on a bare boat charter basis; and <br /> b) the use, maintenance or rental of containers (including trailers and related equipment for the transport of containers) used for the transport of goods and merchandise; <br /> where such rental or such use, maintenance or rental, as the case may be, is incidental to the operation of ships or aircraft in international traffic. <br /> <br />4. The provisions of paragraph 1 shall also apply to profits derived from: <br /> a) selling of tickets on behalf of another enterprise; <br /> b) bank deposits; and <br /> c) bonds, shares, stocks, and other debentures which shall be implemented in accordance with the paragraph 14 and 14.1 of Article 8 in the Commentaries on the Articles of the Model Tax Convention published by OECD in 2017; <br /> provided that such income is incidental to the operations of ships or aircraft. <br /> <br /> <br />Article 9 ASSOCIATED ENTERPRISES <br /> <br />1. Where <br /> a) an enterprise of a Contracting State participates directly or indirectly in the management, control or capital of an enterprise of the other Contracting State, or <br /> b) the same persons participate directly or indirectly in the management, control or capital of an enterprise of a Contracting State and an enterprise of the other Contracting State, <br /> and in either case conditions are made or imposed between the two enterprises in their commercial or financial relations which differ from those which would be made between independent enterprises, then any profits which would, but for those conditions, have accrued to one of the enterprises, but, by reason of those conditions, have not so accrued, may be included in the profits of that enterprise and taxed accordingly. <br /> <br />2. Where a Contracting State includes in the profits of an enterprise of that Contracting State - and taxes accordingly - profits on which an enterprise of the other Contracting State has been charged to tax in that other Contracting State and the profits so included are profits which would have accrued to the enterprise of the first-mentioned Contracting State if the conditions made between the two enterprises had been those which would have been made between independent enterprises, then that other Contracting State shall make an appropriate adjustment to the amount of the tax charged therein on those profits. In determining such adjustment, due regard shall be had to the other provisions of this Convention and the competent authorities of the Contracting States shall if necessary consult each other. <br /> <br /> <br />Article 10 DIVIDENDS <br /> <br />1. Dividends paid by a company which is a resident of a Contracting State to a resident of the other Contracting State may be taxed in that other State. <br /> <br />2. However, dividends paid by a company which is a resident of a Contracting State may also be taxed in the Contracting State according to the laws of that State, but if the beneficial owner of the dividends is a resident of the other Contracting State, the tax so charged shall not exceed: <br /> a) 5 per cent of the gross amount of the dividends if the beneficial owner is a company (other than a partnership) which holds directly at least 10 per cent of the capital of the company paying the dividends; <br /> b) 10 per cent of the gross amount of the dividends in all other cases. <br /> <br /> This paragraph shall not affect the taxation of the company in respect of the profits out of which the dividends are paid. <br /> <br />3. The term "dividends" as used in this Article means income from shares or other rights, not being debt-claims, participating in profits, as well as income from other corporate rights which is subjected to the same taxation treatment as income from shares by the laws of the State of which the company making the distribution is a resident. <br /> <br />4. The provisions of paragraphs 1 and 2 shall not apply if the beneficial owner of the dividends, being a resident of a Contracting State, carries on business in the other Contracting State of which the company paying the dividends is a resident, through a permanent establishment situated therein, and the holding in respect of which the dividends are paid is effectively connected with such permanent establishment. In such case the provisions of Article 7, as the case may be, shall apply. <br /> <br />5. Where a company which is a resident of a Contracting State derives profits or income from the other Contracting State, that other State may not impose any tax on the dividends paid by the company, except insofar as such dividends are paid to a resident of that other State or insofar as the holding in respect of which the dividends are paid is effectively connected with a permanent establishment situated in that other State, nor subject the company's undistributed profits to a tax on the company's undistributed profits, even if the dividends paid or the undistributed profits consist wholly or partly of profits or income arising in such other State. <br /> <br /> <br />Article 11 INTEREST <br /> <br />1. Interest arising in a Contracting State and paid to a resident of the other Contracting State may be taxed in that other State. <br /> <br />2. However, interest arising in a Contracting State may also be taxed in that State in which it arises and according to the laws of that State, but if the beneficial owner of the interest is a resident of the other Contracting State, the tax so charged shall not exceed 10 per cent of the gross amount of the interest. <br /> <br />3. Notwithstanding the provisions of paragraph 2, interest arising in a Contracting State shall be taxable only in the other Contracting State if the interest is beneficially owned by that other Contracting State including political subdivisions and local authorities thereof or any statutory bodies thereof. <br /> <br />4. The term "interest" as used in this Article means income from debt-claims of every kind, whether or not secured by mortgage and whether or not carrying a right to participate in the debtor's profits, and in particular, income from government securities and income from bonds or debentures, including premiums and prizes attaching to such securities, bonds or debentures, as well as income which is subjected to the same taxation treatment as income from money lent by the taxation laws of the Contracting State in which the income arises. <br /> <br />5. The provisions of paragraphs 1 and 2 shall not apply if the beneficial owner of the interest, being a resident of a Contracting State, carries on business in the other Contracting State in which the interest arises through a permanent establishment situated in that other Contracting State and the debt-claim in respect of which the interest is paid is effectively connected with such permanent establishment. In such case, the provisions of Article 7 shall apply. <br /> <br />6. Interest shall be deemed to arise in a Contracting State when the payer is a resident of that Contracting State. Where, however, the person paying the interest, whether he is a resident of a Contracting State or not, has in a Contracting State a permanent establishment in connection with which the indebtedness on which the interest is paid was incurred, and such interest is borne by such permanent establishment, then such interest shall be deemed to arise in the Contracting State in which the permanent establishment is situated. <br /> <br />7. Where, by reason of a special relationship between the payer and the beneficial owner or between both of them and some other person, the amount of the interest, having regard to the debt-claim for which it is paid, exceeds the amount which would have been agreed upon by the payer and the beneficial owner in the absence of such relationship, the provisions of this Article shall apply only to the last-mentioned amount. In such case, the excess part of the payments shall remain taxable according to the laws of each Contracting State, due regard being had to the other provisions of this Convention. <br /> <br /> <br />Article 12 ROYALTIES <br /> <br />1. Royalties arising in a Contracting State and paid to a resident of the other Contracting State may be taxed in that other State. <br /> <br />2. However, royalties arising in a Contracting State may also be taxed in that State according to the laws of that State, but if the beneficial owner of the royalties is a resident of the other Contracting State, the tax so charged shall not exceed 10 per cent of the gross amount of the royalties. <br /> <br />3. The term "royalties" as used in this Article means payments of any kind received as a consideration for the use of, or the right to use, any copyright of literary, artistic or scientific work, including cinematograph films, tapes or other means of reproduction for use in connection with television or radio broadcasting, any patent, trade mark, design or model, plan, secret formula or process, or for information (know-how) concerning industrial, commercial or scientific experience. <br /> <br />4. The provisions of paragraphs 1 and 2 of this Article shall not apply if the beneficial owner of the royalties, being a resident of a Contracting State, carries on business in the other Contracting State in which the royalties arise through a permanent establishment situated in that other Contracting State and the right or property in respect of which the royalties are paid is effectively connected with such permanent establishment. In such case the provisions of Article 7 shall apply. <br /> <br />5. Royalties shall be deemed to arise in a Contracting State when the payer is a resident of that Contracting State. Where, however, the person paying the royalties, whether a resident of a Contracting State or not, has in a Contracting State a permanent establishment in connection with which the liability to pay the royalties was incurred, and such royalties are borne by such permanent establishment, then such royalties shall be deemed to arise in the Contracting State in which the permanent establishment is situated. <br /> <br />6. Where, by reason of a special relationship between the payer and the beneficial owner of the royalties or between both of them and some other person, the amount of the royalties, having regard to the use, right or information for which they are paid, exceeds the amount which would have been agreed upon by the payer and the beneficial owner in the absence of such relationship, the provisions of this Article shall apply only to the last mentioned amount. In such case, the excess part of the payments shall remain taxable according to the laws of each Contracting State, due regard being had to the other provisions of this Convention. <br /> <br /> <br />Article 13 CAPITAL GAINS <br /> <br />1. Gains derived by a resident of a Contracting State from the alienation of immovable property referred to in Article 6 and situated in the other Contracting State may be taxed in that other State. <br /> <br />2. Gains from the alienation of movable property forming part of the business property of a permanent establishment which an enterprise of a Contracting State has in the other Contracting State, including such gains from the alienation of such a permanent establishment (alone or with the whole enterprise), may be taxed in that other State. <br /> <br />3. Gains from the alienation of ships or aircraft operated in international traffic or movable property pertaining to the operation of such ships or aircraft, shall be taxable only in the Contracting State of which the enterprise is a resident. <br /> <br />4. Gains derived by a resident of a Contracting State from the alienation of shares deriving more than 50% of their value directly or indirectly from immovable property situated in the other Contracting State may be taxed in that other State unless the shares are listed on a recognised stock exchange. <br /> <br />5. Gains from the alienation of shares other than those mentioned in paragraph 4 representing a participation of at least 25 per cent in a company which is a resident of a Contracting State may be taxed in that State. The tax so charged shall not exceed 10 per cent of the gains. <br /> <br />6. Gains from the alienation of any property other than that referred to in paragraphs 1, 2, 3, 4 and 5, shall be taxable only in the Contracting State of which the alienator is a resident. <br /> <br />7. For the purposes of Article 13, it is understood that paragraph 5 includes capital gains derived from the alienation of shares, securities or comparable interest in a company, bonds and other debentures, which are taxable only in the Contracting State of which the alienator is a resident. <br /> <br /> <br />Article 14 DEPENDENT PERSONAL SERVICES <br /> <br />1. Subject to the provisions of Articles 15, 17, 18 and 19, salaries, wages and other similar remuneration derived by a resident of a Contracting State in respect of an employment shall be taxable only in that State unless the employment is exercised in the other Contracting State. If the employment is so exercised, such remuneration as is derived therefrom may be taxed in that other State. <br /> <br />2. Notwithstanding the provisions of paragraph 1, remuneration derived by a resident of a Contracting State in respect of an employment exercised in the other Contracting State shall be taxable only in the first-mentioned State if: <br /> a) the recipient is present in the other State for a period or periods not exceeding in the aggregate 183 days in any twelve month period commencing or ending in the fiscal year concerned; <br /> b) the remuneration is paid by, or on behalf of, an employer who is not a resident of the other State; and <br /> c) the remuneration is not borne by a permanent establishment which the employer has in the other State. <br /> <br />3. Notwithstanding the preceding provisions of this Article, remuneration derived in respect of an employment exercised aboard a ship or aircraft operated in international traffic by an enterprise of a Contracting State shall be taxable only in that State. <br /> <br /> <br />Article 15 DIRECTORS' FEES <br /> <br /> Directors' fees and other similar payments derived by a resident of a Contracting State in that person’s capacity as a member of the board of directors of a company which is a resident of the other Contracting State may be taxed in that other State. <br /> <br /> <br />Article 16 ENTERTAINERS AND SPORTSPERSONS <br /> <br />1. Notwithstanding the provisions of Article 14, income derived by a resident of a Contracting State as an entertainer, such as a theatre, motion picture, radio or television artiste, or a musician, or as a sportsperson, from that resident’s personal activities as such exercised in the other Contracting State, may be taxed in that other State. <br /> <br />2. Where income in respect of personal activities exercised by an entertainer or a sportsperson acting as such accrues not to the entertainer or sportsperson but to another person, that income may, notwithstanding the provisions of Articles 7 and 14, be taxed in the Contracting State in which the activities of the entertainer or sportsperson are exercised. <br /> <br />3. Notwithstanding the provisions of paragraphs 1 and 2 of this Article, income derived from such activities performed within the framework of the cultural agreements concluded between the Contracting State are reciprocally exempt from tax only if such activities are sponsored by the Government of a Contracting State or financed by public funds of both Contracting States and the activities are not for profit. <br /> <br /> <br />Article 17 PENSIONS AND ANNUITIES <br /> <br />1. Subject to the provisions of paragraph 2 of Article 18, pensions and other similar remuneration and annuities paid to a resident of a Contracting State in consideration of past employment shall be taxable only in that Contracting State. However such pensions and other similar remuneration and annuities may also be taxed in the other contracting State if they arise in that State. <br /> <br />2. Notwithstanding the provisions of paragraph 1, pensions paid and other payments made under public schemes, which are part of the social security system of a Contracting State or a local authority thereof, shall be taxable only in that Contracting State. <br /> <br />3. When used in this Article: <br /> a) the terms "pensions and other similar remuneration" mean periodic payments made after retirement in consideration of past employment or by way of compensations for injuries received in connection with past employment; <br /> b) the term "annuities" means a stated sum payable to an individual periodically at stated times during life, or during a specified or ascertainable period of them, under an obligation to make the payments in return for adequate and full consideration in money or money’s worth. <br /> <br /> <br />Article 18 GOVERNMENT SERVICE <br /> <br />1. a) Salaries, wages and other similar remuneration paid by a Contracting State or a political subdivision or a local authority thereof to an individual in respect of services rendered to that Contracting State or subdivision or authority shall be taxable only in that Contracting State. <br /> b) However, such salaries, wages and other similar remuneration shall be taxable only in the other Contracting State if the services are rendered in that Contracting State and the individual is a resident of that Contracting State who: <br /> (i) is a national of that Contracting State; or <br /> (ii) did not become a resident of that State solely for the purpose of rendering the services. <br /> <br />2. a) Notwithstanding the provisions of paragraph 1, pensions and other similar remuneration paid by, or out of funds created by, a Contracting State or a political subdivision or a local authority thereof to an individual in respect of services rendered to that Contracting State or subdivision or authority shall be taxable only in that Contracting State. <br /> b) However, such pensions and other similar remuneration shall be taxable only in the other Contracting State if the individual is a resident of, and a national of, that Contracting State. <br /> <br />3. The provisions of Articles 14, 15, 16, and 17 shall apply to salaries, wages, pensions, and other similar remuneration in respect of services rendered in connection with a business carried on by a Contracting State or a political subdivision or a local authority thereof. <br /> <br />4. The provisions of paragraphs 1, 2 and 3 of this Article shall likewise apply in respect of salaries, wages and other similar remuneration or pensions paid by the Central Bank, investment authorities, or any entity or statutory body thereof which is wholly owned directly or indirectly by that Government, political subdivisions or local governments thereof. <br /> <br /> <br />Article 19 STUDENTS <br /> <br />1. Payments which a student or business apprentice who is or was immediately before visiting a Contracting State a resident of the other Contracting State and who is present in the first-mentioned Contracting State solely for the purpose of education or training receives for the purpose of maintenance, education or training shall not be taxed in that State, provided that such payments arise from sources outside that State. <br /> <br />2. In respect of grants, scholarships and remuneration from employment not covered by paragraph 1, a student or business apprentice described in paragraph 1 shall, in addition, be entitled during such education or training to the same exemptions, reliefs or reductions in respect of taxes available to residents of the Contracting State which a student or business apprentice is visiting. <br /> <br /> <br />Article 20 OTHER INCOME <br /> <br />1. Items of income of a resident of a Contracting State, wherever arising, not dealt with in the foregoing Articles of this Convention shall be taxable only in that State. <br /> <br />2. The provisions of paragraph 1 shall not apply to income, other than income from immovable property as defined in paragraph 2 of Article 6, if the recipient of such income, being a resident of a Contracting State, carries on business in the other Contracting State through a permanent establishment situated therein and the right or property in respect of which the income is paid is effectively connected with such permanent establishment. In such case the provisions of Article 7 shall apply. <br /> <br /> <br />Article 21 ELIMINATION OF DOUBLE TAXATION <br /> <br />1. In the case of Korea, double taxation shall be avoided as follows: <br />Subject to the provisions of Korean tax law regarding the allowance as credit against Korean tax of tax payable in any country other than Korea (which shall not affect the general principle hereof); <br /> a) where a resident of Korea derives income from the United Arab Emirates which may be taxed in the United Arab Emirates under the laws of the United Arab Emirates in accordance with the provisions of this Convention, in respect of that income, the amount of the United Arab Emirates tax payable shall be allowed as a credit against the Korean tax payable imposed on that resident. The amount of credit shall not, however, exceed that part of Korean tax as computed before the credit is given, which is appropriate to that income; <br /> b) where the income derived from the United Arab Emirates is dividends paid by a company which is a resident of the United Arab Emirates to a company which is a resident of Korea which owns at least 25 per cent of the voting shares issued by or the capital stock of the company paying the dividends, the credit shall take into account the United Arab Emirates tax payable by the company in respect of the profits out of which such dividends are paid. <br /> <br />2. In the case of the United Arab Emirates, double taxation shall be avoided as follows: <br /> a) where a resident of the United Arab Emirates derives income which, in accordance with the provisions of this Convention, may be taxed in Korea, the United Arab Emirates shall allow as a deduction from the tax on the income of that resident, an amount equal to the income tax paid in Korea. Such deduction in either case shall not, however, exceed that part of the income tax, as computed before the deduction is given, which is attributable, as the case may be, to the income which may be taxed in Korea; <br /> b) where in accordance with any provision of the Convention income derived by a resident of the United Arab Emirates is exempt from tax in the United Arab Emirates, the United Arab Emirates may nevertheless, in calculating the amount of tax on the remaining income of such resident, take into account the exempted income. <br /> <br /> <br />Article 22 NON-DISCRIMINATION <br /> <br />1. Nationals of a Contracting State shall not be subjected in the other Contracting State to any taxation or any requirement connected therewith, which is other or more burdensome than the taxation and connected requirements to which nationals of that other Contracting State in the same circumstances, in particular with respect to residence, are or may be subjected. <br /> <br />2. The taxation on a permanent establishment which an enterprise of a Contracting State has in the other Contracting State shall not be less favourably levied in that other Contracting State than the taxation levied on enterprises of that other State, carrying on the same activities. This provision shall not be construed as obliging a Contracting State to grant to residents of the other Contracting State any personal allowances, reliefs and reductions for taxation purposes on account of civil status or family responsibilities which it grants to its own residents. <br /> <br />3. Except where the provisions of paragraph 1 of Article 9, paragraph 7 of Article 11, or paragraph 6 of Article 12, apply, interest, royalties and other disbursements paid by an enterprise of a Contracting State to a resident of the other Contracting State shall, for the purpose of determining the taxable profits of such enterprise, be deductible under the same conditions as if they had been paid to a resident of the first-mentioned State. <br /> <br />4. Enterprises of a Contracting State, the capital of which is wholly or partly owned or controlled, directly or indirectly, by one or more residents of the other Contracting State, shall not be subjected in the first-mentioned Contracting State to any taxation or any requirement connected therewith which is other or more burdensome than the taxation and connected requirements to which other similar enterprises of the first-mentioned State are or may be subjected. <br /> <br />5. The provisions of this Article shall apply to taxes subject to the Convention. <br /> <br /> <br />Article 23 MUTUAL AGREEMENT PROCEDURE <br /> <br />1. Where a person considers that the actions of one or both of the Contracting States result or will result for that person in taxation not in accordance with the provisions of this Convention, that person may, irrespective of the remedies provided by the domestic law of those Contracting States, present that person’s case to the competent authority of either Contracting State. The case must be presented within three years from the first notification of the action resulting in taxation not in accordance with the provisions of the Convention. <br /> <br />2. The competent authority shall endeavour, if the objection appears to it to be justified and if it is not itself able to arrive at a satisfactory solution, to resolve the case by mutual agreement with the competent authority of the other Contracting State, with a view to the avoidance of taxation which is not in accordance with the Convention. Any agreement reached shall be implemented notwithstanding any time limits in the domestic law of the Contracting States. <br /> <br />3. The competent authorities of the Contracting States shall endeavour to resolve by mutual agreement any difficulties or doubts arising as to the interpretation or application of the Convention. They may also consult together for the elimination of double taxation in cases not provided for in the Convention. <br /> <br />4. The competent authorities of the Contracting States may communicate with each other directly, including through a joint commission consisting of themselves or their representatives, for the purpose of reaching an agreement in the sense of the preceding paragraphs. <br /> <br /> <br />Article 24 EXCHANGE OF INFORMATION <br /> <br />1. The competent authorities of the Contracting States shall exchange such information as is foreseeably relevant for carrying out the provisions of this Convention or to the administration or enforcement of the domestic laws concerning taxes of every kind and description imposed on behalf of the Contracting States, or of their political subdivisions or local authorities, insofar as the taxation thereunder is not contrary to the Convention. The exchange of information is not restricted by Articles 1 and 2. <br /> <br />2. Any information received under paragraph 1 by a Contracting State shall be treated as secret in the same manner as information obtained under the domestic laws of that State and shall be disclosed only to persons or authorities (including courts and administrative bodies) concerned with the assessment or collection of, the enforcement or prosecution in respect of, the determination of appeals in relation to the taxes referred to in paragraph 1, or the oversight of the above. Such persons or authorities shall use the information only for such purposes. They may disclose the information in public court proceedings or in judicial decisions. <br /> <br />3. In no case shall the provisions of paragraphs 1 and 2 be construed so as to impose on a Contracting State the obligation: <br /> a) to carry out administrative measures at variance with the laws and administrative practice of that or of the other Contracting State; <br /> b) to supply information which is not obtainable under the laws or in the normal course of the administration of that or of the other Contracting State; <br /> c) to supply information which would disclose any trade, business, industrial, commercial or professional secret or trade process, or information, the disclosure of which would be contrary to public policy (ordre public). <br /> <br />4. If information is requested by a Contracting State in accordance with this Article, the other Contracting State shall use its information gathering measures to obtain the requested information, even though that other State may not need such information for its own tax purposes. The obligation contained in the preceding sentence is subject to the limitations of paragraph 3 but in no case shall such limitations be construed to permit a Contracting State to decline to supply information solely because it has no domestic interest in such information. <br /> <br />5. In no case shall the provisions of paragraph 3 be construed to permit a Contracting State to decline to supply information, solely because the information is held by a bank, other financial institution, nominee or person acting in an agency or a fiduciary capacity or because the information relates to ownership interests in a person.  <br /> <br /> <br />Article 25 MEMBERS OF DIPLOMATIC MISSIONS AND CONSULAR POSTS <br /> <br /> Nothing in this Convention shall affect the fiscal privileges of members of diplomatic missions or consular posts under the general rules of international law or under the provisions of special agreements. <br /> <br /> <br />Article 26 ENTITLEMENT TO BENEFITS <br /> <br />1. Notwithstanding the application of the other Articles of the Convention, with respect to taxation in the Republic of Korea only the following residents of the United Arab Emirates shall be entitled to the benefits of Articles 7, 8, 10 to 14, 19 and 20: <br /> a) the Federal and the local governments of the United Arab Emirates; <br /> b) a government institution of the United Arab Emirates such as Central Bank of the United Arab Emirates, Abu Dhabi Investment Authority, Abu Dhabi Investment Company, International Petroleum Investment Company (IPIC), Dubai Tourism Department, Dubai Investment and Development Corporation; <br /> c) a company provided that such company can prove that at least 75 per cent of its capital is beneficially owned by the United Arab Emirates and/or by a government institution of the United Arab Emirates and give substantial evidence that the remaining capital is beneficially owned by individuals being residents of the United Arab Emirates and that the company is controlled by the aforementioned residents. <br /> <br />2. Notwithstanding the provisions of paragraph 1, also the following residents of the United Arab Emirates shall be entitled to the benefits of Article 8, 10 and 11: <br /> a) an individual; <br /> b) a company, provided that such company can give substantial evidence that its capital is beneficially owned exclusively by the United Arab Emirates and/or by a government institution of the United Arab Emirates or local governments and/or by individuals being residents of the United Arab Emirates and the company is controlled by the aforementioned residents; <br /> <br />3. A further prerequisite for relief from Korean taxes under paragraphs 1 and 2 is that the company resident in the United Arab Emirates proves that it was not a principal purpose of the company or of the conduct of its business or of the acquisition or maintenance by it of the shareholding or other property from which the income in question is derived to obtain any of such benefits to the advantage of a person who is not a resident of the United Arab Emirates. <br /> <br />4. Relief from Korean taxes under paragraphs 1 to 3 is conditional on confirmation by the competent authority of the United Arab Emirates that the prerequisite mentioned in paragraphs 1 and 2 have been fulfilled. If the authorities of the Republic of Korea have evidence which casts doubt on the statements which have been made by the person to whom the income or capital is allocatable and which have been confirmed by the competent authority of the United Arab Emirates, the latter shall, as far as possible, make fresh inquiries and shall inform the competent authority of the Republic of Korea of the results. In case of disagreement between the competent authorities of the two Contracting States, the procedure under Article 23 shall be applied. <br /> <br />5. Notwithstanding the other provisions of this Convention, a benefit under this Convention shall not be granted in respect of an item of income if it is reasonable to conclude, having regard to all relevant facts and circumstances, that obtaining that benefit was one of the principal purposes of any arrangement or transaction that resulted directly or indirectly in that benefit, unless it is established that granting that benefit in these circumstances would be in accordance with the object and purpose of the relevant provisions of this Convention. <br /> <br />6. Nothing in this Article shall be construed as restricting, in any manner, the application of any provisions of the law of a Contracting State which are designed to prevent the avoidance or evasion of taxes. <br /> <br /> <br />Article 27 MISCELLANEOUS RULES <br /> <br /> The Provisions of this Convention shall not be construed to restrict in any manner any exclusion, exemption, deduction, credit or other allowances now or hereafter accorded: <br /> a) by the laws of a Contracting State in the determination of the tax imposed by that Contacting State; or <br /> b) by any other special arrangement on taxation between the Contracting States or between one of the Contracting States and residents of the other Contracting State. <br /> <br /> <br />Article 28 ENTRY INTO FORCE <br /> <br />1. The Governments of the Contracting States shall notify each other the completion of the procedures required by its law for the bringing into force of this Convention. <br /> <br />2. The Convention shall enter into force thirty days after the date of the later of the notifications referred to in paragraph 1 and its provisions shall have effect: <br /> a) in respect of taxes withheld at source, for amounts payable on or after the first day of January in the first calendar year following that in which this Convention enters into force; and <br /> b) in respect of other taxes, for the taxable years beginning on or after the first day of January in the first calendar year following that in which this Convention enters into force. <br /> <br />3. The Convention between the Republic of Korea and the United Arab Emirates for the avoidance of double taxation and the prevention of fiscal evasion with respect to taxes on income signed at Dubai on 22 September 2003, shall cease to have effect upon the ratification and application of this Convention with respect to the taxes to which the provisions of this Convention apply in accordance with the provisions of paragraph 2. <br /> <br /> <br />Article 29 TERMINATION <br /> <br /> This Convention shall remain in force until terminated by a Contracting State. Either Contracting State may terminate the Convention, through diplomatic channels, by giving written notice of termination at least six months before the end of any calendar year from the fifth year following that in which the Convention entered into force. In such event, the Convention shall cease to have effect: <br /> a) in respect of taxes withheld at source, for amounts payable on or after the first day of January in the first calendar year following that in which the notice is given; and <br /> b) in respect of other taxes, for the taxable year beginning on or after the first day of January in the first calendar year following that in which the notice is given. <br /> <br />　 <br /> IN WITNESS WHEREOF, the undersigned, duly authorised thereto by their respective Governments, have signed this Convention. <br /> <br /> Done in duplicate at Seoul, this 27th day of February 2019, in the Korean, Arabic, and English languages, all three texts being equally authentic. In the case of divergence of interpretation, the English text shall prevail. <br />　 <br /> <br /> <br />For the Republic of Korea　　　　　　　　　　　For the United Arab Emirates <br />　 <br />Protocol <br />　 <br /> <br /> At the moment of signing the Convention between the Republic of Korea and the United Arab Emirates for the Elimination of Double Taxation with Respect to Taxes on Income and the Prevention of Tax Evasion and Avoidance, the Republic of Korea and the United Arab Emirates have agreed that the following provisions shall form an integral part of the Convention. <br /> <br />1. Subject to the provisions of Article 20, nothing in this Convention shall affect the right of the Government of the United Arab Emirates, its political subdivision, local authorities or local Governments to apply its own laws related to the taxation of income derived from petroleum and natural resources; such activities will be taxed according to the laws of the United Arab Emirates. <br /> <br />2. With respect to paragraph 2 of Article 4, subparagraph a) of Article 10, paragraph 3 of Article 11 and paragraph 4 of Article 18 of this Convention, it is understood that the Contracting State, political subdivisions, local authorities, entities or statutory bodies thereof wholly owned directly or indirectly by that Government shall include: <br /> a) In the case of Korea: <br /> (i) the Bank of Korea; <br /> (ii) the Korea Export-Import Bank; <br /> (iii) the Korea Development Bank; <br /> (iv) the Korea Trade Insurance Corporation; <br /> (v) the Korea Trade Investment Promotion Agency; and <br /> any other entity the capital of which is wholly directly or indirectly owned by the federal or local Governments of the Republic of Korea, including a political subdivision and local authority thereof as may be agreed upon from time to time between the Governments of the Contracting States through notifications by the competent authorities. <br /> b) In case of the United Arab Emirates: <br /> (i) Central Bank of the United Arab Emirates; <br /> (ii) Abu Dhabi Investment Authority; <br /> (iii) Emirates Investment Authority; <br /> (iv) Mubadala Investment Company; <br /> (v) Dubai World; <br /> (vi) Investment Corporation of Dubai; and <br /> any other entity the capital of which is wholly directly or indirectly owned by the federal or local Governments of the United Arab Emirates, including a political subdivision and local authority thereof as may be agreed upon from time to time between the Governments of the Contracting States through notifications by the competent authorities. <br /> <br />3. With reference to paragraph 4 of Article 13 of the Convention, it is understood that the term "recognised stock exchange" means: <br /> a) Korea Stock Exchange; <br /> b) Korea Securities Dealers Automated Quotation (KOSDAQ); <br /> c) Dubai Financial Market; <br /> d) Abu Dhabi Securities Exchange; <br /> e) NASDAQ Dubai; <br /> f) Abu Dhabi Global Market; and <br /> g) any other stock exchange which the competent authorities of the Contracting States agree to recognise for the purposes of that Article. <br /> <br />　 <br /> IN WITNESS WHEREOF, the undersigned, duly authorised thereto by their respective Governments, have signed this Protocol. <br /> <br /> Done in duplicate at Seoul, this 27th day of February 2019, in the Korean, Arabic, and English languages, all three texts being equally authentic. In the case of divergence of interpretation, the English text shall prevail. <br /> <br /> <br />　 <br />For the Republic of Korea　　　　　　　　　　For the United Arab Emirates <br /> <br /><br /><br /><br /><br /><br /><br /> </td> 
      </tr> 
     </tbody> 
    </table> 
   </div> 
  </div> 
  <!-- container //--> 
  <!-- 인쇄 layer --> 
  <!-- 화면내 검색 layer --> 
  <script type="text/javaScript" language="javascript" defer="defer">
<!--
$(document).ready(function()
{
    // 화면내 검색 Layer의 별표본문내용 체크박스 Click Event
    $("#bdySearchLayer").delegate("input:checkbox[id=selectSearchByl]", "click", function(e) {
        isBylChkChg = true;
    });
});
//-->
</script> 
  <div class="vwrap8" id="bdySearchLayer" style="display:none; top: 10px; left: 0px;"> 
   <div class="viewla" style="top: 0px; left: 0px;"> 
    <div class="ins"> 
     <div class="inctn"> 
      <input type="radio" id="preBtn" name="srcBtn" class="radio" value="1" />
      <label for="preBtn">위로</label> 
      <input type="radio" id="nextBtn" name="srcBtn" class="radio" value="2" checked="checked" />
      <label for="nextBtn">아래로</label> 
      <input type="checkbox" id="selectSearchJo" class="check" />
      <label for="selectSearchJo" id="labelSelectSearchJo">검색조문선택</label> 
     </div> 
     <div class="inctn" style="padding:0 0 10px 17px;"> 
      <fieldset> 
       <legend>화면내검색 입력 폼</legend> 
       <input type="text" id="bdySearch" name="bdySearch" value="" class="tx" onkeypress="javascript:if(event.keyCode==13){enterBdySearch(event,document.getElementsByName('srcBtn'));return false;}" /> 
       <label for="bdySearch" class="label_b">검색어 입력</label> 
       <a href="javascript:;" onclick="window.bdySearch(document.getElementsByName('srcBtn'));return false;"><img src="/LSW/images/button/btn_seh4.gif" alt="검색" /></a> 
      </fieldset> 
     </div> 
     <div class="inctn" style="padding:0 0 10px 17px;"> 
      <span id="bdyKeyVal"></span> 
     </div> 
    </div> 
   </div> 
  </div> 
  <!-- 화면내 layer //--> 
  <!-- 본문 검색 후 조문 출력 layer --> 
  <div id="divSearchLayer" style="display: none;"> 
   <div class="vwrap2" id="vwrapSearchList" style="left:3px;top:32px;background:none;"> 
    <div class="viewla" style="width:245px;" id="viewSearchList"> 
     <div class="ins" id="searchList" style="overflow: auto;"></div> 
    </div> 
   </div> 
  </div> 
  <!-- 본문 검색 후 조문 출력 layer //--> 
  <!-- Wide 목록저장 layer --> 
  <div class="bx_ly" id="listSaveLayer" style="display:none"> 
   <form id="saveForm" name="saveForm" target="_self" action="#"> 
    <input type="image" title="전송" style="display:none;" alt="전송" /> 
    <input type="hidden" name="save" value="save" /> 
    <input type="hidden" id="saveTabMenuId" name="tabMenuId" /> 
    <input type="hidden" id="lsAstMode2" name="lsAstMode" value="1" />
    <label for="lsAstMode2" class="label_b">모드</label> 
    <input type="hidden" id="saveWhole" name="saveTarget" value="whole" />
    <label for="saveWhole" class="label_b">전체저장</label> 
    <div class="bx_inner" style="margin:1px 0;"> 
     <p class="ly_tit">목록저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideListSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="saveListXLS" name="saveExt" value="xls" checked="checked" /> 
        <label for="saveListXLS">XLS(엑셀)</label> 
        <input type="radio" id="saveListTXT" name="saveExt" value="txt" /> 
        <label for="saveListTXT">TXT(텍스트)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitListSave();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideListSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
    <div id="inputContainer" style="display:none;"></div> 
   </form> 
  </div> 
  <!-- Wide 목록저장 layer //--> 
  <!-- 법령 조문 목록저장 layer --> 
  <div class="bx_ly" id="joListSaveLayer" style="display:none"> 
   <form id="joSaveForm" name="joSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" style="display:none;" alt="전송" /> 
    <input type="hidden" name="save" value="save" /> 
    <input type="hidden" id="lsAstMode3" name="lsAstMode" value="1" />
    <label for="lsAstMode3" class="label_b">모드</label> 
    <input type="hidden" id="saveWhole2" name="saveTarget" value="whole" />
    <label for="saveWhole2" class="label_b">전체저장</label> 
    <div class="bx_inner" style="margin:1px 0;"> 
     <p class="ly_tit">목록저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideJoListSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="saveJoListXLS" name="saveExt" value="xls" checked="checked" /> 
        <label for="saveJoListXLS">XLS(엑셀)</label> 
        <input type="radio" id="saveJoListTXT" name="saveExt" value="txt" /> 
        <label for="saveJoListTXT">TXT(텍스트)</label> 
        <input type="radio" id="saveHWPList" name="saveExt" value="hwp" /> 
        <label for="saveHWPList">한글(본문)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="javascript:submitJoListSave();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="javascript:SaveWindow.hideJoListSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 법령 조문 목록저장 layer //--> 
  <!-- 법령 조문 본문 저장 layer --> 
  <div class="bx_ly" id="joInfoSaveLayer" style="display:none"> 
   <form id="joInfoSaveForm" name="joInfoSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <div class="bx_inner" style="margin:1px 0;"> 
     <p class="ly_tit">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideJoInfoSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont"> 
      <div class="ly_tx_bx" id="joInfoSaveLayerLoding"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="joDocSelectIdHWP" name="saveExt" value="hwp" checked="checked" /> 
        <label for="joDocSelectIdHWP">한글(HWP)</label> 
        <input type="radio" id="joDocSelectIdPDF" name="saveExt" value="pdf" /> 
        <label for="joDocSelectIdPDF">PDF</label> 
        <input type="radio" id="joDocSelectIdDOC" name="saveExt" value="doc" /> 
        <label for="joDocSelectIdDOC">오피스(DOC)</label> 
       </div> 
       <div class="ly_btn_bx"> 
        <a href="javascript:;" class="btn type" onclick="joBeforeSavePrint(); return false;">저장</a> 
        <a href="javascript:;" class="btn type" onclick="SaveWindow.hideJoInfoSave();">닫기</a> 
       </div> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 법령 조문 본문 저장 layer //--> 
  <div class="vwrap7" id="htmlSaveLayer" style="display:none"> 
   <form id="htmlsaveForm" name="htmlsaveForm" target="_self" action="#"> 
    <fieldset> 
     <legend>파일형식 선택</legend> 
     <input type="image" title="전송" alt="전송" style="display:none;" /> 
     <input type="hidden" name="save" value="save" /> 
     <!-- id="save" --> 
     <div class="contwrap" style="margin:1px 0;"> 
      <div class="viewla"> 
       <div class="ins"> 
        <div class="inctn"> 
         <ul> 
          <li class="itit">파일형식</li> 
          <li class="rdi"> <input type="radio" id="saveHtmlHTML" name="saveExt" class="radio" value="html" checked="checked" /><label for="saveHtmlHTML">HTML</label> <input type="radio" id="saveHtmlXLSb" name="saveExt" class="radio" value="xls" /><label for="saveHtmlXLSb">XLS(엑셀)</label> </li> 
         </ul> 
        </div> 
        <!-- button --> 
        <div class="btnc2_1"> 
         <input type="image" onclick="javascript:submitHtmlContent();" src="/LSW/images/button/btn_save2.gif" alt="저장" /> 
         <span class="btn_close"><a href="javascript:;" onkeypress="" onclick="javascript:SaveWindow.hideHtmlSave();"><img src="/LSW/images/button/btn_close2.gif" alt="닫기" /></a></span> 
        </div> 
        <!-- button //--> 
       </div> 
      </div> 
     </div> 
    </fieldset> 
   </form> 
  </div> 
  <!-- 목록저장 layer //--> 
  <!-- 신구조문 저장 layer --> 
  <div class="bx_ly" id="newSaveLayer" style="display:none"> 
   <form id="newSaveForm" name="newSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideNewSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="newSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx" style="width:280px;"> 
        <input type="radio" id="newSaveHTML" name="newSaveExt" value="html" checked="checked" /> 
        <label for="newSaveHTML">HTML</label> 
        <input type="radio" id="newSaveHWP" name="newSaveExt" value="hwp" /> 
        <label for="newSaveHWP">HWP(한글)</label> 
        <input type="radio" id="newSaveXLS" name="newSaveExt" value="xls" /> 
        <label for="newSaveXLS">XLS(엑셀)</label> 
        <input type="radio" id="newSavePDF" name="newSaveExt" value="pdf" /> 
        <label for="newSavePDF">PDF</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitNewContent();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideNewSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 신구조문저장 layer //--> 
  <!-- 일괄 저장 layer --> 
  <div class="bx_ly" id="bulkSaveLayer" style="display:none"> 
   <form id="bulkSaveForm" name="bulkSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideBulkSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="bulkSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="newBulkSaveHWP" name="newBulkSaveExt" value="hwp" checked="checked" /> 
        <label for="newBulkSaveHWP">HWP</label> 
        <input type="radio" id="newBulkSaveHWPX" name="newBulkSaveExt" value="hwpx" /> 
        <label for="newBulkSaveHWPX">HWPX</label> 
        <input type="radio" id="newBulkSavePDF" name="newBulkSaveExt" value="pdf" /> 
        <label for="newBulkSavePDF">PDF</label> 
        <input type="radio" id="newBulkSaveDOC" name="newBulkSaveExt" value="doc" /> 
        <label for="newBulkSaveDOC">DOC</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitBulkSave();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideBulkSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 일괄 저장 layer //--> 
  <!-- 법령비교 저장 layer --> 
  <div class="bx_ly" id="lawCompareSaveLayer" style="display:none"> 
   <form id="lawCompareSaveForm" name="lawCompareSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideLawCompareSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="lawCmpSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="lawCmpSaveHWP" name="lawCmpSaveExt" class="lawCmpSaveExt" value="hwp" checked="checked" /> 
        <label for="lawCmpSaveHWP">한글(HWP)</label> 
        <input type="radio" id="lawCmpSavePDF" name="lawCmpSaveExt" class="lawCmpSaveExt" value="pdf" /> 
        <label for="lawCmpSavePDF">PDF</label> 
        <input type="radio" id="lawCmpSaveDOC" name="lawCmpSaveExt" class="lawCmpSaveExt" value="doc" /> 
        <label for="lawCmpSaveDOC">오피스(DOC)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitLawCompareContent();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideLawCompareSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 법령비교저장 layer //--> 
  <!-- 본문 저장 layer --> 
  <div class="bx_ly" id="infoSaveLayer" style="display:none;"> 
   <form id="infoSaveForm" name="infoSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">목록저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideInfoSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="infoSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="saveHWP" name="saveExt" value="hwp" checked="checked" /> 
        <label for="saveHWP">HWP(한글)</label> 
        <input type="radio" id="saveTXTb" name="saveExt" value="txt" /> 
        <label for="saveTXTb">TXT(텍스트)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitContent();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideInfoSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 본문 저장 layer //--> 
  <!-- 전체 제개정이유 저장 layer --> 
  <div class="bx_ly" id="lsRvsRsnInfoSaveLayer" style="display:none;"> 
   <form id="lsRvsRsnInfoSaveForm" name="lsRvsRsnInfoSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <input type="hidden" name="lsRvsGubun" value="null" /> 
    <div class="bx_inner" style="margin:1px 0;"> 
     <p class="ly_tit" style="margin-top: 0px; margin-bottom: 0px;">목록저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideLsRvsRsnSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont"> 
      <div class="ly_tx_bx" id="lsRvsRsnInfoSaveLayerLoding"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="saveRvsRsnHWP" name="saveExt" value="hwp" checked="checked" /> 
        <label for="saveRvsRsnHWP">HWP(한글)</label> 
        <input type="radio" id="saveRvsRsnTXTb" name="saveExt" value="txt" /> 
        <label for="saveRvsRsnTXTb">TXT(텍스트)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="javascript:submitRvsRsnContent();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideLsRvsRsnSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 전체 제개정이유 저장 layer --> 
  <!-- 학칙공단 제개정문 저장 layer --> 
  <div class="bx_ly" id="schlRvsRsnSaveLayer" style="display:none;"> 
   <form id="schlPubRulSaveForm" name="schlPubRulSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <input type="hidden" id="seq" name="schlPubRulSeq" value="" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">목록 저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideSchlPubRulRvsRsnSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="schlInfoSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="saveSchlHWP" name="saveExt" value="hwp" checked="checked" /> 
        <label for="saveSchlHWP">HWP(한글)</label> 
        <input type="radio" id="saveSchlTXTb" name="saveExt" value="txt" /> 
        <label for="saveSchlTXTb">TXT(텍스트)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitSchlPubRulContent();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideSchlPubRulRvsRsnSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 학칙공단 제개정문 저장 layer //--> 
  <!-- 영문 본문 저장 layer --> 
  <div class="bx_ly" id="engInfoSaveLayer" style="display:none"> 
   <form id="engInfoSaveForm" name="engInfoSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner" style="height: 160px;"> 
     <p class="ly_tit" style="margin: 0 0 10px 0;">목록저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideEngInfoSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" style="padding: 0;"> 
      <div class="ly_tx_bx" style="height: 60px;"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="docSelectIdHWP" name="docSelectId" class="radio" value="hwp" checked="checked" /> 
        <label for="docSelectIdHWP">한글(HWP)</label> 
        <input type="radio" id="docSelectIdPDF" name="docSelectId" class="radio" value="pdf" /> 
        <label for="docSelectIdPDF">PDF</label> 
        <input type="radio" id="docSelectIdDOC" name="docSelectId" class="radio" value="doc" /> 
        <label for="docSelectIdDOC">오피스(DOC)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="engLsBeforeSavePrint();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideEngInfoSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 영문 본문 저장 layer //--> 
  <!-- 다국어 본문 저장 layer --> 
  <div class="bx_ly" id="multiLingualActInfoSaveLayer" style="display:none"> 
   <form id="multiLingualActInfoSaveForm" name="multiLingualActInfoSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner" style="height: 160px;"> 
     <p class="ly_tit" style="margin: 0 0 10px 0;">본문저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideMultiLingualActInfoSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" style="padding: 0;"> 
      <div class="ly_tx_bx" style="height: 60px;"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="multiLsHwp" name="docSelectId" class="radio" value="hwp" checked="checked" /> 
        <label for="multiLsHwp">한글(HWP)</label> 
        <input type="radio" id="multiLsPdf" name="docSelectId" class="radio" value="pdf" /> 
        <label for="multiLsPdf">PDF</label> 
        <input type="radio" id="multiLsDoc" name="docSelectId" class="radio" value="doc" /> 
        <label for="multiLsDoc">오피스(DOC)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="multiLingualActSavePrint();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideMultiLingualActInfoSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 다국어 본문 저장 layer //--> 
  <!-- 법령용어 저장 layer --> 
  <div class="vwrap7" id="lsTrmInfoSaveLayer" style="display:none"> 
   <form id="lsTrmInfoSaveForm" name="lsTrmInfoSaveForm" target="_self" action="#" onsubmit="return lsTrmBeforeSavePrint()"> 
    <fieldset> 
     <legend>파일형식 선택</legend> 
     <input type="image" title="전송" alt="전송" style="display:none;" /> 
     <input type="hidden" id="saveQuery" name="lsTrm" />
     <label for="saveQuery" style="display:none">법령용어명</label> 
     <input type="hidden" name="save" value="save" /> 
     <!--  id="save" --> 
     <div class="contwrap" style="margin:1px 0;"> 
      <div class="viewla"> 
       <div class="ins"> 
        <div class="inctn"> 
         <ul> 
          <li class="itit">파일형식</li> 
          <li class="rdi" style="width:220px;text-align:center;"> <input type="radio" id="lsTrmDocSelectIdHWP" name="lsTrmDocSelectId" class="radio" value="hwp" checked="checked" /><label for="lsTrmDocSelectIdHWP">한글(HWP)</label> <input type="radio" id="lsTrmDocSelectIdPDF" name="lsTrmDocSelectId" class="radio" value="pdf" /><label for="lsTrmDocSelectIdPDF">PDF</label> 
           <!-- <input type="radio" id="docSelectIdDOC" name="docSelectId" class="radio" value="doc" /><label for="docSelectIdDOC">오피스(DOC)</label>--> </li> 
         </ul> 
        </div> 
        <!-- button --> 
        <div class="btnc2_1"> 
         <input type="image" onclick="javascript:lsTrmBeforeSavePrint();return false;" src="/LSW/images/button/btn_save2.gif" alt="저장" /> 
         <span class="btn_close"><a href="javascript:;" onkeypress="" onclick="javascript:SaveWindow.hideInfoSaveNew();"><img src="/LSW/images/button/btn_close2.gif" alt="닫기" /></a></span> 
        </div> 
        <!-- button //--> 
       </div> 
      </div> 
     </div> 
    </fieldset> 
   </form> 
  </div> 
  <!-- 법령용어 저장 layer TXT(텍스트) 저장 추가 //--> 
  <!-- 법령용어 저장 layer --> 
  <div class="bx_lyTrm" id="lsTrmInfoSaveLayer2" style="display:none"> 
   <form id="lsTrmInfoSaveForm2" name="lsTrmInfoSaveForm2" target="_self" action="#" onsubmit="return lsTrmBeforeSavePrint2()"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" id="saveQuery1" name="lsTrm" />
    <label for="saveQuery1" style="display:none">법령용어명</label> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner" style="margin:1px 0;"> 
     <p class="ly_tit">목록저장</p> 
     <button class="btn_clse" onclick="javascript:SaveWindow.hideInfoSaveNew();return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="lsTrmDocSelectIdHWP1" name="saveExt" class="radio" value="hwp" checked="checked" />
        <label for="lsTrmDocSelectIdHWP1">한글(HWP)</label> 
        <input type="radio" id="lsTrmDocSelectIdTXT1" name="saveExt" class="radio" value="txt" />
        <label for="lsTrmDocSelectIdTXT1">TXT(텍스트)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <input type="image" onclick="javascript:lsTrmBeforeSavePrint2();return false;" src="/LSW/images/button/btn_save2.gif" alt="저장" /> 
       <input type="image" onclick="javascript:SaveWindow.hideInfoSaveNew();return false;" src="/LSW/images/button/btn_close2.gif" alt="닫기" /> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 법령용어 저장 layer layer TXT(텍스트) 저장 추가 //--> 
  <!-- 3단비교  저장 layer --> 
  <div class="vwrap7" id="thdCmpSaveLayer" style="display:none"> 
   <form id="thdCmpSaveForm" name="thdCmpSaveForm" target="_self" action="#"> 
    <fieldset> 
     <legend>파일형식 선택</legend> 
     <input type="image" title="전송" alt="전송" style="display:none;" /> 
     <input type="hidden" name="save" value="save" /> 
     <!-- id="save" --> 
     <div class="contwrap" style="margin:1px 0;"> 
      <div class="viewla"> 
       <div class="ins" id="thdCmpSaveLayerLoding"> 
        <div class="inctn"> 
         <ul> 
          <li class="itit">파일형식</li> 
          <li class="rdi"> <input type="radio" id="saveThdCmpHTML" name="saveExt" class="radio" value="html" checked="checked" /><label for="saveThdCmpHTML">HTML</label> <input type="radio" id="saveThdCmpHWP" name="saveExt" class="radio" value="hwp" /><label for="saveThdCmpHWP">HWP(한글)</label> <input type="radio" id="saveThdCmpXLSb" name="saveExt" class="radio" value="xls" /><label for="saveThdCmpXLSb">XLS(엑셀)</label> </li> 
         </ul> 
        </div> 
        <!-- button --> 
        <div class="btnc2_1"> 
         <input type="image" onclick="javascript:submitListSaveThdCmpPrc();return false;" src="/LSW/images/button/btn_save2.gif" alt="저장" /> 
         <span class="btn_close"><a href="javascript:;" onkeypress="" onclick="javascript:SaveWindow.hideThdCmpSave();"><img src="/LSW/images/button/btn_close2.gif" alt="닫기" /></a></span> 
        </div> 
        <!-- button //--> 
       </div> 
      </div> 
     </div> 
    </fieldset> 
   </form> 
  </div> 
  <!-- LUM 3단비교, 법령단위비교 저장 Layer --> 
  <div class="bx_ly" id="thdCmpNewSaveLayer" style="display:none;"> 
   <form id="thdCmpNewSaveForm" name="thdCmpNewSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <input type="hidden" name="chrClsCd" value="010202" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px; margin-bottom: 0px;">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideThdCmpNewSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" style="width: 360px;"> 
      <div class="ly_tx_bx" id="thdCmpNewSaveLayerLoding" style="padding: 12px 8px;"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="saveThdCmpNewHTML" name="saveExt" value="html" checked="checked" /> 
        <label for="saveThdCmpNewHTML">HTML</label> 
        <input type="radio" id="saveThdCmpNewHWP" name="saveExt" value="hwp" /> 
        <label for="saveThdCmpNewHWP">HWP(한글)</label> 
        <input type="radio" id="saveThdCmpNewXLSb" name="saveExt" value="xls" /> 
        <label for="saveThdCmpNewXLSb">XLS(엑셀)</label> 
        <input type="radio" id="saveThdCmpNewPDF" name="saveExt" value="pdf" /> 
        <label for="saveThdCmpNewPDF">PDF</label> 
        <input type="radio" id="saveThdCmpDOC" name="saveExt" value="doc" /> 
        <label for="saveThdCmpDOC">DOC</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="javascript:submitListSaveLumThdCmpPrc();return false;">저장</a> 
       <a href="javascript:;" class="btn type" onclick="javascript:SaveWindow.hideThdCmpNewSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 3단비교 임시 저장 layer --> 
  <div class="vwrap7" id="thdCmpTmpSaveLayer" style="display:none"> 
   <form id="thdCmpTmpSaveForm" name="thdCmpTmpSaveForm" target="_self" action="#"> 
    <fieldset> 
     <legend>파일형식 선택</legend> 
     <input type="image" title="전송" alt="전송" style="display:none;" /> 
     <input type="hidden" name="save" value="save" /> 
     <!-- id="save" --> 
     <div class="contwrap" style="margin:1px 0;"> 
      <div class="viewla"> 
       <div class="ins" id="thdCmpTmpSaveLayerLoding"> 
        <div class="inctn"> 
         <ul> 
          <li class="itit">파일형식</li> 
          <li class="rdi"> <input type="radio" id="saveThdCmpTmpSaveHTML" name="saveExt" class="radio" value="html" checked="checked" /><label for="saveThdCmpTmpSaveHTML">HTML</label> <input type="radio" id="saveThdCmpTmpSaveXLSb" name="saveExt" class="radio" value="xls" /><label for="saveThdCmpTmpSaveXLSb">XLS(엑셀)</label> <input type="radio" id="saveThdCmpTmpSaveHWP" name="saveExt" class="radio" value="hwp" /><label for="saveThdCmpTmpSaveHWP">HWP(한글)</label> </li> 
         </ul> 
        </div> 
        <!-- button --> 
        <div class="btnc2_1"> 
         <input type="image" onclick="javascript:submitListSaveThdCmpTmpPrc();return false;" src="/LSW/images/button/btn_save2.gif" alt="저장" /> 
         <span class="btn_close"><a href="javascript:;" onkeypress="" onclick="javascript:SaveWindow.hideThdCmpTmpSave();"><img src="/LSW/images/button/btn_close2.gif" alt="닫기" /></a></span> 
        </div> 
        <!-- button //--> 
       </div> 
      </div> 
     </div> 
    </fieldset> 
   </form> 
  </div> 
  <!-- 행정규칙 신구조문 저장 layer --> 
  <div class="bx_ly" id="admRulOANSaveLayer" style="display:none"> 
   <form id="admRulOANSaveForm" name="admRulOANSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideAdmRulOANSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="admRulOANSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="admRulOANSaveHTML" name="admRulOANSaveExt" value="html" checked="checked" /> 
        <label for="admRulOANSaveHTML">HTML</label> 
        <input type="radio" id="admRulOANSaveHWP" name="admRulOANSaveExt" value="hwp" /> 
        <label for="admRulOANSaveHWP">HWP(한글)</label> 
        <input type="radio" id="admRulOANSaveXLS" name="admRulOANSaveExt" value="xls" /> 
        <label for="admRulOANSaveXLS">XLS(엑셀)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitAdmRulOAN();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideAdmRulOANSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 행정규칙 신구조문저장 layer //--> 
  <!-- 학칙규정 신구조문 저장 layer --> 
  <div class="bx_ly" id="schlPubRulOANSaveLayer" style="display:none"> 
   <form id="schlPubRulOANSaveForm" name="schlPubRulOANSaveForm" target="_self" action="#"> 
    <input type="image" title="전송" alt="전송" style="display:none;" /> 
    <input type="hidden" name="save" value="save" /> 
    <div class="bx_inner"> 
     <p class="ly_tit" style="margin-top: 0px;margin-bottom: 0px;">내용저장</p> 
     <button class="btn_clse" onclick="SaveWindow.hideSchlPubRulOANSave(); return false;"> <span class="blind">닫기</span> </button> 
     <div class="ly_cont" id="schlPubRulOANSaveLayerLoding"> 
      <div class="ly_tx_bx"> 
       <p class="tx">파일형식</p> 
       <div class="ly_inp_bx"> 
        <input type="radio" id="schlPubRulOANSaveHTML" name="schlPubRulOANSaveExt" value="html" checked="checked" /> 
        <label for="schlPubRulOANSaveHTML">HTML</label> 
        <input type="radio" id="schlPubRulOANSaveHWP" name="schlPubRulOANSaveExt" value="hwp" /> 
        <label for="schlPubRulOANSaveHWP">HWP(한글)</label> 
        <input type="radio" id="schlPubRulOANSaveXLS" name="schlPubRulOANSaveExt" value="xls" /> 
        <label for="schlPubRulOANSaveXLS">XLS(엑셀)</label> 
       </div> 
      </div> 
      <div class="ly_btn_bx"> 
       <a href="javascript:;" class="btn type" onclick="submitSchlPubRulOAN();">저장</a> 
       <a href="javascript:;" class="btn type" onclick="SaveWindow.hideSchlPubRulOANSave();">닫기</a> 
      </div> 
     </div> 
    </div> 
   </form> 
  </div> 
  <!-- 학칙규정 신구조문저장 layer //-->   
  <script type="text/javascript" src="/LSW/js/common/hrefRemove.js"></script>  
 </body>
</html>