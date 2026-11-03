<!DOCTYPE html>
<html lang="ko">
<head>
<link rel="shortcut icon" href="/images/favicon.ico" type="image/x-icon" />
<title>제도소개</title>
<meta property="og:type" content="website">
<meta property="og:title" content="국세청">
<meta name="keywords" content="국세청">
<meta name="description" content="국세청 홈페이지에 오신 것을 환영합니다. ">
<meta property="og:image" content="/images/nts/layout/logo.png">
<meta property="og:url" content="https://www.nts.go.kr/">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta http-equiv="X-UA-Compatible" content="IE=Edge" />
<meta name="viewport" content="width=device-width,initial-scale=1.0,minimum-scale=1.0,maximum-scale=3.0,user-scalable=yes" />
<!-- <link rel="stylesheet" href="/common/js/mCustomScrollbar/jquery.mCustomScrollbar.min.css" /> -->
<link rel="stylesheet" type="text/css" href="/css/web/nts/sub.css?ver=3" />
<link rel="stylesheet" type="text/css" href="/css/web/nts/layout.css?ver=5" />
<script src="/js/jquery.min.js"></script>
<script src="/js/jquery-ui.min.js"></script>
<script src="/js/jquery.form.min.js"></script>
<script src="/js/jquery.showLoading.js"></script>
<!-- <script src="/common/js/mCustomScrollbar/jquery.mCustomScrollbar.concat.min.js"></script> -->
<script src="/common/js/jquery.bxslider.js"></script>
<script src="/common/js/imageMapResizer/src/imageMapResizer.js"></script>
<script src="/common/js/con_com.js"></script>
<script src="/js/web/nts/layout.js"></script>
<script src="/js/web/nts/sub.js"></script> 
<script src="/js/web/nts/w3cReplace.js?ver=1"></script>
<!-- 게시판 관련 -->		
<script src="/common/js/board.js?ver=1"></script><!-- 게시판 js -->
<script src="/js/common.js?ver=2"></script>

<script src="/js/search/ntsSearch.js"></script>
<link rel="stylesheet" href="/css/com/jquery-ui/jquery-ui.css" media="all">

<link rel="stylesheet" href="/js/keyboard/keyboard.css" media="all">
<script src="/js/keyboard/keyboard.min.js"></script>



<!--[if lt IE 9]>
<script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
<script src="https://oss.maxcdn.com/libs/respond.js/1.3.0/respond.min.js"></script>
<![endif]-->
</head>
<body>
<div id="skipNav">
        <a href="#gnb">주메뉴 바로가기</a>
        <a href="#container">본문으로 바로가기</a>
    </div>
    <div class="eg">
	    <div class="egBar">
	        <p>
	       		<img src="/images/web/nts/main/eg_logo.png" alt="태극기">이 누리집은 대한민국 공식 전자정부 누리집입니다.
	        </p>
	   		<!-- <div class="util">
				<a href="https://www.nts.go.kr/english/main.do" class="globus" target="_blank" title="영문홈페이지 새창이동"><span>ENG<em class="noShowM">LISH</em></span></a>
			</div> -->
	    </div>
	</div>
	
	<header id="header">
		<div class="bgMenuBar"><div class="inner"></div></div>
		<div class="utilWrap">
			<div class="container">
				<div class="utilInner">
					<div class="util">
						<a href="https://www.nts.go.kr/english/main.do" class="globus" target="_blank" title="영문홈페이지 새창이동"><span>ENG<em class="noShowM">LISH</em></span></a>
					</div>
					<div class="fontSize">
						<span class="name">화면크기</span>
						<span class="btns">
							<a href="javascript:scaleOut();" class="btnR"><em class="sr-only">화면크기 축소</em></a>
							<a href="javascript:scaleInit();" class="btnO"><em class="sr-only">화면크기 원래대로</em></a>
							<a href="javascript:scaleIn();" class="btnE"><em class="sr-only">화면크기 확대</em></a>
						</span>
					</div>
				</div>
				<div class="logos">
					<h1>
						<a href="/nts/main.do" class="logo1"><span class="sr-only">국세청</span></a>
					</h1>
					<!-- <a href="https://www.president.go.kr/affairs/gov_project" class="logo2" target="_blank" title="대한민국 대통령실 120대 국정과제 새창이동">
						<span ><em class="sr-only">다시 대한민국! 새로운 국민의 나라</em></span>
					</a> -->
					<!-- <span class="logo2"><em class="sr-only">다시 대한민국! 새로운 국민의 나라</em></span> --> 
				</div>
				<div id="totalSearch">
					<h2 class="sr-only">검색창</h2>
					<!-- <form name="search" id="search" method="post" action="/search/search.jsp" class="clearfix" onsubmit="return false;"> -->
					<form name="search" id="search" method="post" action="/search/search.jsp" target="searchFrame" class="clearfix" onsubmit="showSearchArea();">					
						<input type="hidden" name="sysid" id="sysid" value="nts" />
						<input type="hidden" name="collection" id="collection"/>
						<fieldset>
							<legend class="query">통합검색</legend>
							<label for="query" hidden>검색어 입력창</label>
							<input type="search" name="query" id="query" placeholder="검색어를 입력하세요" title="검색어 입력" onKeypress="javascript:pressCheck((event),this);" autocomplete="off">
							<div id="hunminKbArea"></div>							
							<button id="openKeyBoard" title="가상키보드 레이어 열림"><img src="/images/web/nts/layout/icon-keyboard.png" alt="키보드"/></button>
							<!--  placeholder="검색어를 입력하세요." -->
							<button onClick="javascript:doSearch();" class="totalSchBtn totalSchBtn" title="검색"><span class="sr-only">검색</span></button>
							<a href="#totalSearch" class="btnSearchClose hashClose"><em class="sr-only">검색창 닫기</em></a>
						</fieldset>
					</form>
				</div>
				<!-- <ul class="snsLst">
					<li><a href="http://www.youtube.com/ntskorea" title="국세청 유투브 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns06.png" alt="유투브"></a></li>
					<li><a href="https://www.instagram.com/nts.korea/" title="국세청 인스타그램 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns09.png" alt="인스타그램"></a></li>
					<li><a href="http://www.facebook.com/ntsKorea" title="국세청 페이스북 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns02.png" alt="페이스북"></a></li>
					<li><a href="http://blog.naver.com/ntscafe/" title="국세청 네이버 블로그 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns01.png" alt="네이버 블로그"></a></li>
					<li><a href="https://x.com/ntsKorea" title="국세청 X 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns08.png" alt="X"></a></li>
					<li><a href="http://story.kakao.com/ch/nts" title="국세청 카카오스토리 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns05.png" alt="카카오스토리"></a></li>
					<li><a href="https://post.naver.com/my.nhn?memberNo=4795084" title="국세청 네이버 포스트  새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns04.png" alt="네이버 포스트"></a></li>					
				</ul> -->
				
			</div>
		</div>
		<div class="menuWrap">
			<div class="container">
				<a href="#fullMenu" id="btn_fullMenu" class="allMenu hash"><em>전체메뉴</em></a>
				<!--START-->
				<div id="mainMenu">
					<ul class="gnb" id="gnb">
						<li><a href="/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028" title="알림·소식">알림·소식</a>
							<ul class="depth2">
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028" title="보도자료 ">보도자료 </a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=41090&bbsId=50849" title="국민체감 성과">국민체감 성과</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2202&bbsId=1035" title="신문기사 모음">신문기사 모음</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2203&bbsId=1041" title="보도설명 자료">보도설명 자료</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2203&bbsId=1041" title="정정자료">정정자료</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41100&bbsId=50853" title="반론자료">반론자료</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41099&bbsId=50852" title="설명자료">설명자료</a></li>
									</ul>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2205&bbsId=1120" title="고시∙공고∙행정예고">고시∙공고∙행정예고</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2205&bbsId=1120" title="고시">고시</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2206&bbsId=1122" title="공고">공고</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=6420&bbsId=1102" title="훈령∙고시 행정예고">훈령∙고시 행정예고</a></li>
									</ul>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2207&bbsId=1011" title="공지사항">공지사항</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2209&bbsId=1022" title="국세청 소식">국세청 소식</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2209&bbsId=1022" title="소식지(뉴스레터)">소식지(뉴스레터)</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2210&bbsId=1034" title="국세">국세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11923&cntntsId=8630" title="사회공헌">사회공헌</a></li>
									</ul>
								</li>
								<li><a href="/nts/prgn/selectPrgnTaxpyerBdList.do?mi=2214" title="모범납세자">모범납세자</a>
								</li>
								<li><a href="/nts/outwr/selectOutwrAgentBdInfo.do?mi=40648" title="국선대리인">국선대리인</a>
							</ul>
						</li>
						<li><a href="/nts/ad/cntnts/cntntsView.do?mi=13366" title="국민소통" class="now">국민소통</a>
							<ul class="depth2">
								<li><a href="/nts/ad/cntnts/cntntsView.do?mi=13366" title="국세청100배 활용하기 가이드맵">국세청100배 활용하기 가이드맵</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13346&cntntsId=8654" title="규제혁신">규제혁신</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13346&cntntsId=8654" title="규제혁신 신문고">규제혁신 신문고</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6714&cntntsId=8121" title="규제혁신 과제현황">규제혁신 과제현황</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6715&cntntsId=8122" title="심사중인 규제법안">심사중인 규제법안</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6716&cntntsId=8123" title="부처별 보도자료">부처별 보도자료</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6717&cntntsId=8124" title="규제법령 정보">규제법령 정보</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13347&cntntsId=8655" title="규제입증 요청">규제입증 요청</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126" title="적극행정">적극행정</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126" title="제도소개">제도소개</a></li>
										<li	class="window"><a href="https://www.mpm.go.kr/proactivePublicService/activeRecommand/recommendation" target="_blank" title="적극행정 국민추천(새창)" >적극행정 국민추천</a></li>
										<li	class="window"><a href="https://www.epeople.go.kr/nep/pttn/negativePttn/NegativePttnCotents.npaid" target="_blank" title="소극행정 신고(새창)" >소극행정 신고</a></li>
										<li	class="window"><a href="https://www.mpm.go.kr/proactivePublicService/local/localNotice" target="_blank" title="적극행정 자료실(새창)" >적극행정 자료실</a></li>
									</ul>
								</li>
								<li	class="window"><a href="/taxpayer_advocate/main.do?mi=132011" target="_blank" title="납세자권익 24(새창)" >납세자권익 24</a>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="국세신고안내" class="return ">국세신고안내</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="개인신고안내" class="emphasis">개인신고안내</a>
									<div class="depth3Wrap">
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="종합소득세">종합소득세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2246&cntntsId=7678" title="주택임대소득">주택임대소득</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2265&cntntsId=7690" title="종교인소득">종교인소득</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2272&cntntsId=7693" title="부가가치세">부가가치세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2283&cntntsId=7699" title="사업장현황신고">사업장현황신고</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2289&cntntsId=7701" title="원천세">원천세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2304&cntntsId=238938" title="연말정산">연말정산</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2308&cntntsId=7707" title="양도소득세">양도소득세</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40989&bbsId=50822" title="밑줄 쫙, 부동산세금 체크포인트">밑줄 쫙, 부동산세금 체크포인트</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40671&bbsId=50810" title="국세청이 알려주는 양도(종부)세 실수사례">국세청이 알려주는 양도(종부)세 실수사례</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40395&bbsId=50729" title="양도소득세 월간 질의 TOP10">양도소득세 월간 질의 TOP10</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40552&bbsId=50790" title="상속 · 증여 안심 가이드">상속 · 증여 안심 가이드</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2324&cntntsId=7718" title="상속세">상속세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2338&cntntsId=7726" title="증여세">증여세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2351&cntntsId=7733" title="종합부동산세">종합부동산세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2364&cntntsId=7741" title="세금납부 안내">세금납부 안내</a></li>
									</ul>
									</div>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2370&cntntsId=7744" title="법인신고안내" class="emphasis">법인신고안내</a>
									<div class="depth3Wrap">
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2370&cntntsId=7744" title="법인세">법인세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2388&cntntsId=7751" title="공익법인">공익법인</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2401&cntntsId=7693" title="부가가치세">부가가치세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2413&cntntsId=7701" title="원천세">원천세</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6645&cntntsId=238938" title="연말정산">연말정산</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2431&cntntsId=7690" title="종교인소득">종교인소득</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2438&cntntsId=7774" title="세금납부 안내">세금납부 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40375&cntntsId=7733" title="종합부동산세">종합부동산세</a></li>
									</ul>
									</div>
								</li>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2443&cntntsId=7776" title="국세정책/제도" class="return ">국세정책/제도</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40999&cntntsId=239048" title="세무조사 제도">세무조사 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40999&cntntsId=239048" title="세무조사 개요">세무조사 개요</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41000&cntntsId=239049" title="법인사업자 정기조사 선정기준">법인사업자 정기조사 선정기준</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41021&cntntsId=239050" title="개인사업자 정기조사 선정기준">개인사업자 정기조사 선정기준</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41105&bbsId=50854" title="세무조사 중점검증항목">세무조사 중점검증항목</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41022&bbsId=50827" title="주요서식">주요서식</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2443&cntntsId=7776" title="사업자등록 안내">사업자등록 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2443&cntntsId=7776" title="사업자등록 안내">사업자등록 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2444&cntntsId=7777" title="사업자등록 신청">사업자등록 신청</a></li>
										<li><a href="/nts/ad/cntnts/cntntsView.do?mi=2445" title="제출서류 및 교부">제출서류 및 교부</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2446&cntntsId=7779" title="사업자등록 정정">사업자등록 정정</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2447&cntntsId=7780" title="휴∙폐업">휴∙폐업</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2448&bbsId=30664" title="자주묻는 질문 답변">자주묻는 질문 답변</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2479&cntntsId=7801" title="온라인취약업종 세무 안내">온라인취약업종 세무 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2479&cntntsId=7801" title="1인미디어 창작자">1인미디어 창작자</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2482&cntntsId=7803" title="SNS마켓 사업자">SNS마켓 사업자</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2485&cntntsId=7805" title="공유숙박 사업자">공유숙박 사업자</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40541&bbsId=50762" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2489&bbsId=50666" title="동영상자료실">동영상자료실</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2450&cntntsId=7781" title="근로∙자녀장려금">근로∙자녀장려금</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2450&cntntsId=7781" title="근로장려금 소개">근로장려금 소개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2451&cntntsId=7782" title="자녀장려금 소개">자녀장려금 소개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2452&cntntsId=7783" title="신청자격">신청자격</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40397&cntntsId=238977" title="신청기간 및 방법">신청기간 및 방법</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2453&cntntsId=7784" title="심사 및 지급">심사 및 지급</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2455&bbsId=30046" title="주요서식">주요서식</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2456&bbsId=30047" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=7267&bbsId=50664" title="동영상자료실">동영상자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2457&bbsId=1148" title="카드뉴스">카드뉴스</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41125&cntntsId=239080" title="청년지원정책">청년지원정책</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41125&cntntsId=239080" title="스타트업 세금든든케어">스타트업 세금든든케어</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41126&cntntsId=239081" title="세무조사 유예 및 시기선택">세무조사 유예 및 시기선택</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41127&cntntsId=239082" title="세액감면 및 절세혜택">세액감면 및 절세혜택</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41128&cntntsId=239083" title="창업멘토링 및 공감소통">창업멘토링 및 공감소통</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41129&cntntsId=239084" title="조세지원제도">조세지원제도</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41130&cntntsId=239085" title="징수유예 등">징수유예 등</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41131&cntntsId=239086" title="주류시장 진입 완화">주류시장 진입 완화</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41132&cntntsId=239087" title="학자금 상환유예">학자금 상환유예</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41133&cntntsId=239088" title="체납액 특례제도">체납액 특례제도</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41134&cntntsId=239089" title="납세자 세금신고">납세자 세금신고</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2460&cntntsId=7786" title="전자(세금)계산서/현금영수증/신용카드">전자(세금)계산서/현금영수증/신용카드</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2460&cntntsId=7786" title="전자(세금)계산서">전자(세금)계산서</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2468&cntntsId=7793" title="현금영수증∙신용카드">현금영수증∙신용카드</a></li>
									</ul>
								</li>
								<li><a href="#?mi=40250" title="전자기부금영수증 제도">전자기부금영수증 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40251&cntntsId=238907" title="제도 안내">제도 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40252&cntntsId=238908" title="전자기부금영수증 발급 시스템 운영">전자기부금영수증 발급 시스템 운영</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40253&bbsId=50691" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40254&bbsId=50692" title="자주 묻는 질문">자주 묻는 질문</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41102&cntntsId=239068" title="전자송달 제도">전자송달 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41102&cntntsId=239068" title="제도 안내">제도 안내</a></li>
									</ul>
								</li>
								<li><a href="#?mi=40533" title="가업승계 세무컨설팅">가업승계 세무컨설팅</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40594&cntntsId=239010" title="제도안내">제도안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40595&cntntsId=239011" title="신청 방법 및 대상자 선정">신청 방법 및 대상자 선정</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40599&bbsId=50796" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40593&bbsId=50793" title="동영상자료실">동영상자료실</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41093&cntntsId=239070" title="소득세 공제감면 컨설팅 제도">소득세 공제감면 컨설팅 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41093&cntntsId=239070" title="제도 안내">제도 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41094&cntntsId=239071" title="신청방법 및 혜택">신청방법 및 혜택</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2498&cntntsId=7809" title="법인세 공제감면 컨설팅 제도">법인세 공제감면 컨설팅 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2498&cntntsId=7809" title="제도 안내">제도 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2499&cntntsId=7810" title="신청방법 및 혜택">신청방법 및 혜택</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40543&bbsId=50768" title="주요서식 작성요령/사례 ">주요서식 작성요령/사례 </a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41121&bbsId=50855" title="동영상자료실">동영상자료실</a></li>
									</ul>
								</li>
								<li><a href="#?mi=40623" title="과세정보 사전수요/ 비밀유지 확인 컨설팅">과세정보 사전수요/ 비밀유지 확인 컨설팅</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40584&cntntsId=239005" title="과세정보 사전 수요 컨설팅">과세정보 사전 수요 컨설팅</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40625&cntntsId=239016" title="비밀유지 확인 컨설팅">비밀유지 확인 컨설팅</a></li>
									</ul>
								</li>
								<li><a href="#?mi=40030" title="착한임대인 세액공제 제도">착한임대인 세액공제 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40005&cntntsId=238883" title="소개">소개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40041&cntntsId=238889" title="핵심 가이드">핵심 가이드</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40255&bbsId=50693" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a></li>
										<li><a href="/comm/nttFileDownload.do?fileKey=2daacbc878d6b3b17221d15c96735dc1&mi=40368" title="세액공제 계산">세액공제 계산</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40006&bbsId=50671" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40007&bbsId=50670" title="자주 묻는 질문">자주 묻는 질문</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40031&bbsId=50672" title="카드뉴스/리플릿">카드뉴스/리플릿</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40302&bbsId=50695" title="동영상자료실">동영상자료실</a></li>
									</ul>
								</li>
								<li><a href="#?mi=40369" title="가상자산소득 과세제도">가상자산소득 과세제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40370&cntntsId=238935" title="가상자산소득 과세 개요">가상자산소득 과세 개요</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40372&cntntsId=238937" title="가상자산사업자 거래자료 제출">가상자산사업자 거래자료 제출</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40400&bbsId=50734" title="주요서식">주요서식</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40386&bbsId=50720" title="참고자료실">참고자료실</a></li>
									</ul>
								</li>
								<li><a href="#?mi=40346" title="소득자료 제출 안내">소득자료 제출 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40347&cntntsId=238923" title="실시간 소득파악 제도 안내">실시간 소득파악 제도 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40348&cntntsId=238924" title="소득자료별 제출안내">소득자료별 제출안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40990&cntntsId=239045" title="소득자료별 제출방법 및 유의사항">소득자료별 제출방법 및 유의사항</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40313&bbsId=50712" title="주요서식">주요서식</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40312&bbsId=50713" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40314&bbsId=50714" title="동영상자료실">동영상자료실</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41085&cntntsId=239067" title="명의도용 안심차단 서비스 안내">명의도용 안심차단 서비스 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41085&cntntsId=239067" title="제도안내">제도안내</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41087&bbsId=50844" title="자주 묻는 질문">자주 묻는 질문</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41088&bbsId=50845" title="주요서식">주요서식</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41089&bbsId=50846" title="참고자료실">참고자료실</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2510&cntntsId=7817" title="국제조세정보">국제조세정보</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2510&cntntsId=7817" title="해외동향 및 세무정보">해외동향 및 세무정보</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2513&cntntsId=7819" title="국제조세 주요 신고제도">국제조세 주요 신고제도</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2516&bbsId=1103" title="조세조약 및 법령정보">조세조약 및 법령정보</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2520&cntntsId=7822" title="자금출처확인서 발급안내">자금출처확인서 발급안내</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=13452&bbsId=131012" title="발간책자">발간책자</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2522&bbsId=30061" title="참고자료실">참고자료실</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2521&bbsId=30060" title="주요서식">주요서식</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2491&cntntsId=8086" title="명의신탁주식 실소유자 확인안내">명의신탁주식 실소유자 확인안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2491&cntntsId=8086" title="제도 안내">제도 안내</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=17206&bbsId=30670" title="주요서식">주요서식</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=17225&bbsId=30671" title="참고자료실">참고자료실</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2565&cntntsId=7853" title="조세소송">조세소송</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2526&cntntsId=7823" title="세법해석 질의 안내">세법해석 질의 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2526&cntntsId=7823" title="세법해석 질의 안내">세법해석 질의 안내</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2530&cntntsId=7826" title="서면질의제도">서면질의제도</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2536&cntntsId=7830" title="세법해석 사전답변제도">세법해석 사전답변제도</a></li>
										<li><a href="/comm/nttFileDownload.do?fileKey=9bd03fa9e354c7b0871536f30ebda388&mi=2539" title="신청∙답변대상이 아닌 사례">신청∙답변대상이 아닌 사례</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=16358&bbsId=30667" title="자주묻는질문">자주묻는질문</a></li>
									</ul>
								</li>
								<li><a href="/nts/ad/nf/nltFormatApiList.do?mi=40178" title="세무서식">세무서식</a>
								</li>
								<li><a href="#?mi=2545" title="통합자료실">통합자료실</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=7133&bbsId=1083" title="국세청 발간책자">국세청 발간책자</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2544&bbsId=1099" title="국세청 프로그램">국세청 프로그램</a></li>
										<li	class="window"><a href="https://taxlaw.nts.go.kr/st/USESTJ001M.do" target="_blank" title="세무용어사전(새창)" >세무용어사전</a></li>
										<li><a href="/nts/ad/taxSchdul/selectList.do?mi=135747" title="세무일정">세무일정</a></li>
									</ul>
								</li>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13447&amp;cntntsId=8663" title="정보공개">정보공개</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13447&amp;cntntsId=8663" title="정보공개">정보공개</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13447&cntntsId=8663" title="정보공개제도 안내">정보공개제도 안내</a></li>
										<li><a href="/nts/pdoc/openApi/list.do?mi=6409" title="정보목록">정보목록</a></li>
										<li	class="window"><a href="https://www.open.go.kr" target="_blank" title="정보공개 청구(새창)" >정보공개 청구</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=6411&bbsId=1075" title="일반행정정보">일반행정정보</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=6413&bbsId=1067" title="예산현황">예산현황</a></li>
									</ul>
								</li>
								<li><a href="/nts/ad/od/openDataList.do?mi=6679" title="사전정보공표">사전정보공표</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6685&cntntsId=8097" title="고액 상습체납자 등 명단 공개">고액 상습체납자 등 명단 공개</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6685&cntntsId=8097" title="고액 상습체납자 명단 공개">고액 상습체납자 명단 공개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6686&cntntsId=8098" title="조세포탈범 명단 공개">조세포탈범 명단 공개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40981&cntntsId=239041" title="세금계산서 발급의무 등 위반자 명단공개">세금계산서 발급의무 등 위반자 명단공개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6687&cntntsId=8099" title="해외금융계좌 고액 신고 의무 위반자 명단 공개">해외금융계좌 고액 신고 의무 위반자 명단 공개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135731&cntntsId=8101" title="불성실기부금수령단체 명단 공개">불성실기부금수령단체 명단 공개</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6690&cntntsId=8102" title="공공데이터 제공">공공데이터 제공</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=6691&bbsId=1138" title="정책 실명제">정책 실명제</a>
								</li>
								<li	class="window"><a href="https://www.prism.go.kr/homepage" target="_blank" title="정책연구보고서(새창)" >정책연구보고서</a>
								</li>
								<li	class="window"><a href="https://tasis.nts.go.kr" target="_blank" title="국세통계포털(새창)" >국세통계포털</a>
							</ul>
						</li>
						<li><a href="#?mi=6731" title="국세청 소개">국세청 소개</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6729&cntntsId=8131" title="국세청안내">국세청안내</a>
									<ul class="depth3">
										<li	class="window"><a href="https://call.nts.go.kr/call/cm/cntnts/cntntsView.do?mi=2074&cntntsId=7041" target="_blank" title="대표상담전화(새창)" >대표상담전화</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6732&cntntsId=8133" title="연혁">연혁</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6738&cntntsId=8139" title="국세청 상징">국세청 상징</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6740&cntntsId=8140" title="조직과 기능">조직과 기능</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6748&cntntsId=8148" title="국세청에서 하는 일">국세청에서 하는 일</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6750&cntntsId=8149" title="열린국세청">열린국세청</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6755&cntntsId=8154" title="차장 소개">차장 소개</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6756&cntntsId=8155" title="역대 청장 소개">역대 청장 소개</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6758&cntntsId=8156" title="국세공무원 소개">국세공무원 소개</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6758&cntntsId=8156" title="국세공무원이란">국세공무원이란</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6759&cntntsId=8157" title="국세청공무원행동강령">국세청공무원행동강령</a></li>
									</ul>
								</li>
								<li><a href="/nts/taxSrch/taxSrchPage.do?mi=6761" title="전국 세무관서">전국 세무관서</a>
									<ul class="depth3">
										<li><a href="/nts/taxSrch/taxSrchPage.do?mi=6761" title="지역으로 찾기">지역으로 찾기</a></li>
										<li><a href="/nts/imArea/selectImAreaNmList.do?mi=6762" title="이름으로 찾기">이름으로 찾기</a></li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6767&cntntsId=8163" title="찾아오시는 길">찾아오시는 길</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13322&cntntsId=8648" title="인천공항 납세지원센터">인천공항 납세지원센터</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13322&cntntsId=8648" title="민원증명 신청">민원증명 신청</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13323&cntntsId=8649" title="각종 신고서 접수">각종 신고서 접수</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13324&cntntsId=8650" title="각종 신청 접수">각종 신청 접수</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13325&cntntsId=8651" title="기타 이용가능 업무">기타 이용가능 업무</a></li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13329&cntntsId=8652" title="인천국제공항 비즈니스센터 운영">인천국제공항 비즈니스센터 운영</a></li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=15630&bbsId=30665" title="자주묻는 질문 답변">자주묻는 질문 답변</a></li>
									</ul>
								</li>
								<li	class="window"><a href="https://teht.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/ca/e/c/UTECAECA05.xml" target="_blank" title="세무서 민원실 대기인원조회(새창)" >세무서 민원실 대기인원조회</a>
								</li>
							</ul>
						</li>
					</ul>
				</div>
				<!--END-->
				<script type="text/javascript">
				var keyboard = new hunminKB({keyLayout:'KOREAN', offset: {top:300, left:50}});
				var keyOfficeLeft = $("#header .menuWrap .container").offset().left + $("#header .menuWrap .container").width() - 245;				
				$(function(){$('#openKeyBoard').mouseup(function() {
						keyboard.keyboardAction(this, {						
						inputElement: '#query',
						offset: {top: 102,left: 0}
						});
						/*웹접근성 관련 수정 20250807 Yang*/
						$('#hunminKBLayout li:first-child > button').focus();	
					});
					
				});
				
				</script>
				<a href="#totalSearch" class="btnSearch hash"><em class="sr-only">검색창 열기</em></a>
				
			</div>
		</div>
		<div id="fullMenu">
			<a href="#fullMenu" class="allMenu hashClose"><i class="xi-close-thin"></i><em class="sr-only">전체메뉴 닫힘</em></a>
			<div class="container">
				<div class="util">
					<a href="https://hometax.go.kr" target="_blank" title="홈택스 바로가기(새창)">홈택스</a>
					<a href="https://taxlaw.nts.go.kr" target="_blank" title="국세법령정보 바로가기(새창)">국세법령정보</a>
					<a href="/nts/taxSrch/taxSrchPage.do?mi=6761" title="지방청·세무서 바로가기(새창)">지방청&middot;세무서</a>
					<a href="https://call.nts.go.kr" target="_blank" title="국세상담센터 바로가기(새창)">국세상담센터</a>
					<a href="https://www.nts.go.kr/english/main.do" class="globus" target="_blank" title="영문홈페이지 바로가기(새창)"><span>ENGLISH</span></a>
				</div>
				<div class="snsLstBox">
					<ul class="snsLst">
						<li><a href="http://www.youtube.com/ntskorea" title="국세청 유투브 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns06.png" alt="유투브"></a></li>
						<li><a href="https://www.instagram.com/nts.korea/" title="국세청 인스타그램 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns09.png" alt="인스타그램"></a></li>
						<li><a href="http://www.facebook.com/ntsKorea" title="국세청 페이스북 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns02.png" alt="페이스북"></a></li>
						<li><a href="http://blog.naver.com/ntscafe/" title="국세청 네이버 블로그 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns01.png" alt="네이버 블로그"></a></li>
						<li><a href="https://x.com/ntsKorea" title="국세청 X 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns08.png" alt="X"></a></li>
						<li><a href="http://story.kakao.com/ch/nts" title="국세청 카카오스토리 새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns05.png" alt="카카오스토리"></a></li>
						<!-- <li><a href="https://post.naver.com/my.nhn?memberNo=4795084" title="국세청 네이버 포스트  새창열림" target="_blank"><img src="/images/web/nts/main/icon_sns04.png" alt="네이버 포스트"></a></li> -->
					</ul>
				</div>
				<ul class="gnb">
				<!--START-->
						<li><a href="/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028" title="알림·소식" style='text-decoration:none; cursor:default'>알림·소식</a>
							<ul class="depth2">
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028" title="보도자료 ">보도자료 </a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=41090&bbsId=50849" title="국민체감 성과">국민체감 성과</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2202&bbsId=1035" title="신문기사 모음">신문기사 모음</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2203&bbsId=1041" title="보도설명 자료">보도설명 자료</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2203&bbsId=1041" title="정정자료">정정자료</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41100&bbsId=50853" title="반론자료">반론자료</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41099&bbsId=50852" title="설명자료">설명자료</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2205&bbsId=1120" title="고시∙공고∙행정예고">고시∙공고∙행정예고</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2205&bbsId=1120" title="고시">고시</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2206&bbsId=1122" title="공고">공고</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=6420&bbsId=1102" title="훈령∙고시 행정예고">훈령∙고시 행정예고</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2207&bbsId=1011" title="공지사항">공지사항</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=2209&bbsId=1022" title="국세청 소식">국세청 소식</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2209&bbsId=1022" title="소식지(뉴스레터)">소식지(뉴스레터)</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2210&bbsId=1034" title="국세">국세</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11923&cntntsId=8630" title="사회공헌">사회공헌</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11923&cntntsId=8630" title="사회공헌 현황">사회공헌 현황</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=11924&bbsId=5007" title="사회공헌 소식">사회공헌 소식</a>
											</li>
										</ul>
									</li>
								</ul>
								<li><a href="/nts/prgn/selectPrgnTaxpyerBdList.do?mi=2214" title="모범납세자">모범납세자</a>
								</li>
								<li><a href="/nts/outwr/selectOutwrAgentBdInfo.do?mi=40648" title="국선대리인">국선대리인</a>
								</li>
							</ul>
						</li>
						<li><a href="/nts/ad/cntnts/cntntsView.do?mi=13366" title="국민소통" style='text-decoration:none; cursor:default'>국민소통</a>
							<ul class="depth2">
								<li><a href="/nts/ad/cntnts/cntntsView.do?mi=13366" title="국세청100배 활용하기 가이드맵">국세청100배 활용하기 가이드맵</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13354&cntntsId=8656" title="국세청 동영상">국세청 동영상</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13355&cntntsId=109134" title="국세청 SNS ">국세청 SNS </a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13358&cntntsId=109135" title="뉴스레터·PCRM">뉴스레터·PCRM</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13361&cntntsId=109136" title="국세">국세</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13362&cntntsId=109140" title="어린이 국세청 ">어린이 국세청 </a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13363&cntntsId=109143" title="국세법령정보">국세법령정보</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13364&cntntsId=7848" title="국세상담센터126">국세상담센터126</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13365&cntntsId=109144" title="인터넷 세법상담">인터넷 세법상담</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13367&cntntsId=109145" title="서면질의·사전답변">서면질의·사전답변</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13368&cntntsId=109147" title="세법령 개정건의">세법령 개정건의</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13370&cntntsId=109148" title="납세자 세법교실">납세자 세법교실</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13372&cntntsId=109152" title="국립조세박물관">국립조세박물관</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13373&cntntsId=109153" title="국세통계포털">국세통계포털</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6695&cntntsId=109193" title="고객의소리(VOC)">고객의소리(VOC)</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6707&cntntsId=109195" title="국민참여·제안">국민참여·제안</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6710&cntntsId=8118" title="정책토론">정책토론</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6709&cntntsId=8117" title="전자공청회">전자공청회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6708&cntntsId=8116" title="설문조사">설문조사</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13387&cntntsId=8657" title="고액상습체납자 은닉재산신고">고액상습체납자 은닉재산신고</a>
										</li>
										<li><a href="https://hometax.go.kr/websquare/websquare.wq?w2xPath=/ui/pp/index_pp.xml&amp;tmIdx=47&amp;tm2lIdx=4710000000&amp;tm3lIdx=4710080000" target="_blank" title="근로·자녀장려금 부정수급자 신고(새창으로 이동됩니다.)" >근로·자녀장려금 부정수급자 신고</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13389&cntntsId=8659" title="지급명세서 미제출·허위제출 신고">지급명세서 미제출·허위제출 신고</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13390&cntntsId=8660" title="불공정 주류 거래 신고">불공정 주류 거래 신고</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13393&cntntsId=8662" title="예산낭비 신고센터">예산낭비 신고센터</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13395&cntntsId=109150" title="주류제조아카데미">주류제조아카데미</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13398&cntntsId=109159" title="성실신고 간담회">성실신고 간담회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13399&cntntsId=109160" title="금융기관 간담회">금융기관 간담회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13402&cntntsId=109161" title="지급명세서 개발자 간담회">지급명세서 개발자 간담회</a>
										</li>
										<li><a href="#?mi=13403" title="현금영수증 사업자 간담회">현금영수증 사업자 간담회</a>
										</li>
										<li><a href="#?mi=13404" title="주류업단체 간담회">주류업단체 간담회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13406&cntntsId=109174" title="국세행정개혁위원회">국세행정개혁위원회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13407&cntntsId=109175" title="국세행정포럼">국세행정포럼</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135733&cntntsId=109146" title="부패행위신고">부패행위신고</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135734&cntntsId=109149" title="국세통계센터">국세통계센터</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135736&cntntsId=109151" title="금융정보자동교환 설명회">금융정보자동교환 설명회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135737&cntntsId=109156" title="해외세정책자">해외세정책자</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135738&cntntsId=109154" title="납세자권익24">납세자권익24</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135739&cntntsId=109137" title="영세납세자지원단">영세납세자지원단</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135740&cntntsId=109138" title="혁신성장 세정지원">혁신성장 세정지원</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135741&cntntsId=109139" title="상호합의·APA 사전상담">상호합의·APA 사전상담</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135742&cntntsId=109141" title="재산평가심의위원회">재산평가심의위원회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135743&cntntsId=109142" title="해외 세무설명회">해외 세무설명회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135744&cntntsId=109155" title="탈세제보">탈세제보</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135745&cntntsId=109177" title="국세법령해석심의위원회">국세법령해석심의위원회</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41122&cntntsId=239077" title="사업자 차명계좌 신고">사업자 차명계좌 신고</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13346&cntntsId=8654" title="규제혁신">규제혁신</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13346&cntntsId=8654" title="규제혁신 신문고">규제혁신 신문고</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6714&cntntsId=8121" title="규제혁신 과제현황">규제혁신 과제현황</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6715&cntntsId=8122" title="심사중인 규제법안">심사중인 규제법안</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6716&cntntsId=8123" title="부처별 보도자료">부처별 보도자료</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6717&cntntsId=8124" title="규제법령 정보">규제법령 정보</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13347&cntntsId=8655" title="규제입증 요청">규제입증 요청</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126" title="적극행정">적극행정</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126" title="제도소개">제도소개</a>
										</li>
										<li><a href="https://www.mpm.go.kr/proactivePublicService/activeRecommand/recommendation" target="_blank" title="적극행정 국민추천(새창으로 이동됩니다.)" >적극행정 국민추천</a>
										</li>
										<li><a href="https://www.epeople.go.kr/nep/pttn/negativePttn/NegativePttnCotents.npaid" target="_blank" title="소극행정 신고(새창으로 이동됩니다.)" >소극행정 신고</a>
										</li>
										<li><a href="https://www.mpm.go.kr/proactivePublicService/local/localNotice" target="_blank" title="적극행정 자료실(새창으로 이동됩니다.)" >적극행정 자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="/taxpayer_advocate/main.do?mi=132011" target="_blank" title="납세자권익 24(새창으로 이동됩니다.)" >납세자권익 24</a>
								</li>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="국세신고안내" style='text-decoration:none; cursor:default'>국세신고안내</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="개인신고안내">개인신고안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="종합소득세">종합소득세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2224&cntntsId=7664" title="종합소득세 개요">종합소득세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40483&cntntsId=238978" title="모두채움 신고 안내(납부)">모두채움 신고 안내(납부)</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41095&cntntsId=239072" title="모두채움 신고 안내(환급)">모두채움 신고 안내(환급)</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2225&cntntsId=7665" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2226&cntntsId=7666" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2227&cntntsId=7667" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2228&cntntsId=7668" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40296&cntntsId=238910" title="신고·납부방법">신고·납부방법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2230&cntntsId=7669" title="장부기장의무 안내">장부기장의무 안내</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2230&cntntsId=7669" title="기장의무 판단">기장의무 판단</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2231&cntntsId=7670" title="간편장부 안내">간편장부 안내</a></li>
													</ul>
												</li>
												<li><a href="/comm/nttFileDownload.do?fileKey=c51048065d32c285e41951bb0442989e&mi=2233" title="경비율적용 방법 안내">경비율적용 방법 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2234&cntntsId=7672" title="성실신고확인제도 안내">성실신고확인제도 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2236&cntntsId=7673" title="중간예납 안내">중간예납 안내</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2240&bbsId=30683" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2241&bbsId=3066" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2243&bbsId=30000" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40526&bbsId=131038" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2246&cntntsId=7678" title="주택임대소득">주택임대소득</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2246&cntntsId=7678" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2246&cntntsId=7678" title="과세 개요">과세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2247&cntntsId=7679" title="분리과세">분리과세</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2248&cntntsId=7680" title="소형주택 임대사업자에 대한 세액 감면">소형주택 임대사업자에 대한 세액 감면</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2249&cntntsId=7681" title="주택 보증금에 대한 간주임대료">주택 보증금에 대한 간주임대료</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2251&cntntsId=7682" title="주택임대소득 신고안내">주택임대소득 신고안내</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2251&cntntsId=7682" title="과세대상 및 비과세, 과세미달">과세대상 및 비과세, 과세미달</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2253&cntntsId=7684" title="주택임대 소득세 계산">주택임대 소득세 계산</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2254&cntntsId=7685" title="소형주택 임대사업자에 대한 세액감면 계산 사례">소형주택 임대사업자에 대한 세액감면 계산 사례</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2255&cntntsId=7686" title="주택임대소득 신고 절세 Tip">주택임대소득 신고 절세 Tip</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=15732&cntntsId=8798" title="주택임대업의 사업자등록">주택임대업의 사업자등록</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2259&bbsId=30684" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2260&bbsId=30002" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2261&bbsId=30673" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40529&bbsId=50619" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2265&cntntsId=7690" title="종교인소득">종교인소득</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2265&cntntsId=7690" title="종교인소득 과세 개요">종교인소득 과세 개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2266&cntntsId=7691" title="종교인소득 신고">종교인소득 신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2267&cntntsId=7692" title="종교단체 원천징수 및 연말정산">종교단체 원천징수 및 연말정산</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40170&cntntsId=238899" title="종교인소득 지급명세서 제출">종교인소득 지급명세서 제출</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2268&bbsId=30004" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2269&bbsId=30005" title="참고자료실">참고자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2272&cntntsId=7693" title="부가가치세">부가가치세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2272&cntntsId=7693" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2272&cntntsId=7693" title="부가가치세 개요">부가가치세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2273&cntntsId=7694" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2274&cntntsId=7695" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2275&cntntsId=7696" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2276&cntntsId=7697" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/a/a/UTXPPADA01.xml" target="_blank" title="전자적 용역을 제공하는 국외사업자의 신고(새창으로 이동됩니다.)" >전자적 용역을 제공하는 국외사업자의 신고</a>
												</li>
												<li><a href="/nts/ad/nf/nltFormatApiList.do?mi=40178&amp;searchSe=select&amp;selectCode=type10&amp;selectLawNm=부가가치세법" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2279&bbsId=30007" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=9623&cntntsId=8249" title="주요해석사례">주요해석사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2280&bbsId=30008" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40323&bbsId=131039" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2283&cntntsId=7699" title="사업장현황신고">사업장현황신고</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2283&cntntsId=7699" title="사업장현황신고 개요">사업장현황신고 개요</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2284&bbsId=131010" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2285&bbsId=30010" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2286&bbsId=131040" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2289&cntntsId=7701" title="원천세">원천세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2289&cntntsId=7701" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2289&cntntsId=7701" title="원천징수 개요">원천징수 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2290&cntntsId=7702" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2291&cntntsId=7703" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2292&cntntsId=7704" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=12242&cntntsId=8631" title="지급명세서 제출">지급명세서 제출</a>
												</li>
												<li><a href="https://www.hometax.go.kr/websquare/websquare.wq?w2xPath=/ui/pp/index_pp.xml&tmIdx=2900000000&tm2lIdx=2905000000&tm3lIdx=2905010000" target="_blank" title="근로소득간이세액표(새창으로 이동됩니다.)" >근로소득간이세액표</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6769&cntntsId=8165" title="근로소득">근로소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6441&cntntsId=7877" title="퇴직소득">퇴직소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6449&cntntsId=7885" title="연금소득">연금소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6454&cntntsId=7890" title="기타소득">기타소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6464&cntntsId=7900" title="사업소득">사업소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6469&cntntsId=7905" title="금융(이자·배당)소득">금융(이자·배당)소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6480&cntntsId=7916" title="비거주자 원천징수">비거주자 원천징수</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=135790&bbsId=30012" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2301&bbsId=30013" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40398&bbsId=50731" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2304&cntntsId=238938" title="연말정산">연말정산</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2304&cntntsId=238938" title="연말정산 종합 안내">연말정산 종합 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2305&cntntsId=7706" title="편리한 연말정산 이용방법">편리한 연말정산 이용방법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40609&cntntsId=239021" title="맞춤형 안내">맞춤형 안내</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2306&bbsId=30014" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6489&bbsId=30682" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2308&cntntsId=7707" title="양도소득세">양도소득세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2308&cntntsId=7707" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2308&cntntsId=7707" title="양도소득세 개요">양도소득세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2309&cntntsId=7708" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2310&cntntsId=7709" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2311&cntntsId=7710" title="장기보유특별공제율">장기보유특별공제율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2312&cntntsId=7711" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2313&cntntsId=7712" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2314&cntntsId=7713" title="신고납부안내">신고납부안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=12270&cntntsId=8639" title="세액계산요령">세액계산요령</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2317&cntntsId=7716" title="양도신고서별제출증빙서류">양도신고서별제출증빙서류</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40305&cntntsId=238916" title="양도소득세법령적용가이드맵">양도소득세법령적용가이드맵</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2319&bbsId=30016" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2320&bbsId=30017" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2321&bbsId=30018" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=12278&bbsId=131041" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40989&bbsId=50822" title="밑줄 쫙, 부동산세금 체크포인트">밑줄 쫙, 부동산세금 체크포인트</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40671&bbsId=50810" title="국세청이 알려주는 양도(종부)세 실수사례">국세청이 알려주는 양도(종부)세 실수사례</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40395&bbsId=50729" title="양도소득세 월간 질의 TOP10">양도소득세 월간 질의 TOP10</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40552&bbsId=50790" title="상속 · 증여 안심 가이드">상속 · 증여 안심 가이드</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2324&cntntsId=7718" title="상속세">상속세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2324&cntntsId=7718" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2324&cntntsId=7718" title="상속세 개요">상속세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2325&cntntsId=7719" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2326&cntntsId=7720" title="세액계산흐름도">세액계산흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2327&cntntsId=7721" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2328&cntntsId=7722" title="신고시 유의사항">신고시 유의사항</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6522&cntntsId=7950" title="항목별 설명">항목별 설명</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2330&cntntsId=7723" title="상속재산의 평가">상속재산의 평가</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2331&cntntsId=7724" title="상속세 납부">상속세 납부</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2332&cntntsId=7725" title="상속재산의 확인">상속재산의 확인</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40344&cntntsId=238919" title="가업승계 지원제도">가업승계 지원제도</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2333&bbsId=30020" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2334&bbsId=30021" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40256&bbsId=50694" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2338&cntntsId=7726" title="증여세">증여세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2338&cntntsId=7726" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2338&cntntsId=7726" title="증여세 개요">증여세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2339&cntntsId=7727" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2340&cntntsId=7728" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2341&cntntsId=7729" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2342&cntntsId=7730" title="신고시 유의사항">신고시 유의사항</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6533&cntntsId=7960" title="항목별 설명">항목별 설명</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40384&cntntsId=238932" title="일감 몰아·떼어주기 증여의제">일감 몰아·떼어주기 증여의제</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40384&cntntsId=238932" title="일감몰아주기 과세개요">일감몰아주기 과세개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40364&cntntsId=238933" title="일감떼어주기 과세개요">일감떼어주기 과세개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40366&cntntsId=238934" title="세액계산흐름도">세액계산흐름도</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2344&cntntsId=7731" title="증여재산의 평가">증여재산의 평가</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2345&cntntsId=7732" title="증여세 납부">증여세 납부</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2346&bbsId=30023" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6770&bbsId=30024" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6771&bbsId=30025" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=41062&bbsId=50839" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2351&cntntsId=7733" title="종합부동산세">종합부동산세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2351&cntntsId=7733" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2351&cntntsId=7733" title="종합부동산세 개요">종합부동산세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2352&cntntsId=7734" title="납부기한">납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2353&cntntsId=7735" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2354&cntntsId=7736" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2355&cntntsId=7737" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2356&cntntsId=7738" title="납부 종합 안내">납부 종합 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2357&cntntsId=7739" title="궁금해요 종합부동산 세법">궁금해요 종합부동산 세법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6539&cntntsId=7966" title="합산배제 및 과세특례 신고">합산배제 및 과세특례 신고</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2359&bbsId=131026" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2362&bbsId=131042" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2364&cntntsId=7741" title="세금납부 안내">세금납부 안내</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2364&cntntsId=7741" title="국세전자납부 안내">국세전자납부 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2365&cntntsId=7742" title="신용카드납부 안내">신용카드납부 안내</a>
											</li>
										</ul>
									</li>
								</ul>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2370&cntntsId=7744" title="법인신고안내">법인신고안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2370&cntntsId=7744" title="법인세">법인세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2370&cntntsId=7744" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2370&cntntsId=7744" title="법인세 개요">법인세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2371&cntntsId=7745" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2372&cntntsId=7746" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2373&cntntsId=7747" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6544&cntntsId=7970" title="신고시유의사항">신고시유의사항</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6549&cntntsId=7975" title="법인세 신고절차">법인세 신고절차</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6551&cntntsId=7977" title="영리법인 신고 안내">영리법인 신고 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41110&cntntsId=239090" title="AI 기업을 위한 세제혜택 안내">AI 기업을 위한 세제혜택 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6556&cntntsId=7982" title="비영리법인 신고 안내">비영리법인 신고 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6561&cntntsId=7987" title="법인세 공제감면">법인세 공제감면</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6565&cntntsId=7991" title="법인세 중간예납">법인세 중간예납</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2380&cntntsId=7999" title="동업기업 과세특례">동업기업 과세특례</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2381&cntntsId=8001" title="연결납세제도">연결납세제도</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2382&cntntsId=7748" title="성실신고확인제">성실신고확인제</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2383&cntntsId=7749" title="연구인력개발비 세액공제 사전 심사제도">연구인력개발비 세액공제 사전 심사제도</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=135784&bbsId=30028" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2386&bbsId=30669" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40246&bbsId=50689" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2388&cntntsId=7751" title="공익법인">공익법인</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2388&cntntsId=7751" title="공익법인 개요">공익법인 개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2389&cntntsId=7752" title="세제 혜택">세제 혜택</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2390&cntntsId=7753" title="상증법상 각종 의무">상증법상 각종 의무</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2391&cntntsId=7754" title="보고서 등 제출">보고서 등 제출</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2392&cntntsId=7755" title="결산서류 등 공시">결산서류 등 공시</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40413&cntntsId=238948" title="공익법인등 주식보유 관련 의무이행 신고">공익법인등 주식보유 관련 의무이행 신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40101&cntntsId=238894" title="최근 주요 개정세법">최근 주요 개정세법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=12297&cntntsId=8647" title="공익법인등(구·지정기부금단체) 지정추천 신청">공익법인등(구·지정기부금단체) 지정추천 신청</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2394&cntntsId=7757" title="공익법인등(구·지정기부금단체)의 의무사항">공익법인등(구·지정기부금단체)의 의무사항</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40647&cntntsId=239037" title="공익단체">공익단체</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2395&cntntsId=7758" title="기부장려금 제도">기부장려금 제도</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40393&cntntsId=238944" title="공익법인 주기적 감사인 지정제도">공익법인 주기적 감사인 지정제도</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40645&cntntsId=239030" title="공익법인 특수관계인 해당여부 사전상담제 ">공익법인 특수관계인 해당여부 사전상담제 </a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2397&cntntsId=7760" title="주요세법 해석사례">주요세법 해석사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2398&bbsId=30031" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2399&bbsId=131043" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2401&cntntsId=7693" title="부가가치세">부가가치세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2401&cntntsId=7693" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2401&cntntsId=7693" title="부가가치세 개요">부가가치세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2402&cntntsId=238927" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2403&cntntsId=238928" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2405&cntntsId=7697" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/ad/nf/nltFormatApiList.do?mi=40178&amp;searchSe=select&amp;selectCode=type10&amp;selectLawNm=부가가치세법" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2408&bbsId=30007" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2409&bbsId=30008" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40327&bbsId=131039" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2413&cntntsId=7701" title="원천세">원천세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2413&cntntsId=7701" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2413&cntntsId=7701" title="원천징수 개요">원천징수 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2414&cntntsId=7702" title="신고납부기한">신고납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2415&cntntsId=7703" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2416&cntntsId=7704" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=12309&cntntsId=8631" title="지급명세서 제출">지급명세서 제출</a>
												</li>
												<li><a href="https://teht.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/sf/a/a/UTESFAAF99.xml" target="_blank" title="근로소득간이세액표(새창으로 이동됩니다.)" >근로소득간이세액표</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6582&cntntsId=8165" title="근로소득">근로소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6597&cntntsId=7877" title="퇴직소득">퇴직소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6605&cntntsId=7885" title="연금소득">연금소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6610&cntntsId=7890" title="기타소득">기타소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6620&cntntsId=7900" title="사업소득">사업소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40351&cntntsId=7905" title="금융(이자·배당)소득">금융(이자·배당)소득</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6636&cntntsId=7916" title="비거주자 원천징수">비거주자 원천징수</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=135800&bbsId=30012" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2425&bbsId=30013" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40399&bbsId=50731" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6645&cntntsId=238938" title="연말정산">연말정산</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6645&cntntsId=238938" title="연말정산 종합 안내">연말정산 종합 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6646&cntntsId=7706" title="편리한 연말정산 이용방법">편리한 연말정산 이용방법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40629&cntntsId=239021" title="맞춤형 안내">맞춤형 안내</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6647&bbsId=30014" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6648&bbsId=30682" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2431&cntntsId=7690" title="종교인소득">종교인소득</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2431&cntntsId=7690" title="종교인소득 과세 개요">종교인소득 과세 개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2432&cntntsId=7691" title="종교인소득 신고">종교인소득 신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2433&cntntsId=7692" title="종교단체 원천징수 및 연말정산">종교단체 원천징수 및 연말정산</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2434&bbsId=30004" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=2435&bbsId=30005" title="참고자료실">참고자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2438&cntntsId=7774" title="세금납부 안내">세금납부 안내</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2438&cntntsId=7774" title="국세전자납부 안내">국세전자납부 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2439&cntntsId=7775" title="신용카드납부 안내">신용카드납부 안내</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40375&cntntsId=7733" title="종합부동산세">종합부동산세</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40375&cntntsId=7733" title="기본정보">기본정보</a>
													<ul class="depth5">
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40375&cntntsId=7733" title="종합부동산세 개요">종합부동산세 개요</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40376&cntntsId=7734" title="납부기한">납부기한</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40377&cntntsId=7735" title="세액계산 흐름도">세액계산 흐름도</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40378&cntntsId=7736" title="세율">세율</a></li>
														<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40379&cntntsId=7737" title="가산세">가산세</a></li>
													</ul>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40380&cntntsId=7738" title="납부 종합 안내">납부 종합 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40401&cntntsId=7739" title="궁금해요 종합부동산 세법">궁금해요 종합부동산 세법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40404&cntntsId=7966" title="합산배제 및 과세특례 신고">합산배제 및 과세특례 신고</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40410&bbsId=131026" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40411&bbsId=131042" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
									</ul>
								</li>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2443&cntntsId=7776" title="국세정책/제도" style='text-decoration:none; cursor:default'>국세정책/제도</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40999&cntntsId=239048" title="세무조사 제도">세무조사 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40999&cntntsId=239048" title="세무조사 개요">세무조사 개요</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41000&cntntsId=239049" title="법인사업자 정기조사 선정기준">법인사업자 정기조사 선정기준</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41021&cntntsId=239050" title="개인사업자 정기조사 선정기준">개인사업자 정기조사 선정기준</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41105&bbsId=50854" title="세무조사 중점검증항목">세무조사 중점검증항목</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41022&bbsId=50827" title="주요서식">주요서식</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2443&cntntsId=7776" title="사업자등록 안내">사업자등록 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2443&cntntsId=7776" title="사업자등록 안내">사업자등록 안내</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2444&cntntsId=7777" title="사업자등록 신청">사업자등록 신청</a>
										</li>
										<li><a href="/nts/ad/cntnts/cntntsView.do?mi=2445" title="제출서류 및 교부">제출서류 및 교부</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2446&cntntsId=7779" title="사업자등록 정정">사업자등록 정정</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2447&cntntsId=7780" title="휴∙폐업">휴∙폐업</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2448&bbsId=30664" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2479&cntntsId=7801" title="온라인취약업종 세무 안내">온라인취약업종 세무 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2479&cntntsId=7801" title="1인미디어 창작자">1인미디어 창작자</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2479&cntntsId=7801" title="개요">개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2480&cntntsId=7802" title="세무 안내">세무 안내</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=15595&bbsId=30632" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2482&cntntsId=7803" title="SNS마켓 사업자">SNS마켓 사업자</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2482&cntntsId=7803" title="개요">개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2483&cntntsId=7804" title="세무 안내">세무 안내</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=15599&bbsId=30635" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2485&cntntsId=7805" title="공유숙박 사업자">공유숙박 사업자</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2485&cntntsId=7805" title="개요">개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2486&cntntsId=7806" title="세무 안내">세무 안내</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=15605&bbsId=30639" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40541&bbsId=50762" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2489&bbsId=50666" title="동영상자료실">동영상자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2450&cntntsId=7781" title="근로∙자녀장려금">근로∙자녀장려금</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2450&cntntsId=7781" title="근로장려금 소개">근로장려금 소개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2451&cntntsId=7782" title="자녀장려금 소개">자녀장려금 소개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2452&cntntsId=7783" title="신청자격">신청자격</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40397&cntntsId=238977" title="신청기간 및 방법">신청기간 및 방법</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2453&cntntsId=7784" title="심사 및 지급">심사 및 지급</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2455&bbsId=30046" title="주요서식">주요서식</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2456&bbsId=30047" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=7267&bbsId=50664" title="동영상자료실">동영상자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2457&bbsId=1148" title="카드뉴스">카드뉴스</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41125&cntntsId=239080" title="청년지원정책">청년지원정책</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41125&cntntsId=239080" title="스타트업 세금든든케어">스타트업 세금든든케어</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41126&cntntsId=239081" title="세무조사 유예 및 시기선택">세무조사 유예 및 시기선택</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41127&cntntsId=239082" title="세액감면 및 절세혜택">세액감면 및 절세혜택</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41128&cntntsId=239083" title="창업멘토링 및 공감소통">창업멘토링 및 공감소통</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41129&cntntsId=239084" title="조세지원제도">조세지원제도</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41130&cntntsId=239085" title="징수유예 등">징수유예 등</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41131&cntntsId=239086" title="주류시장 진입 완화">주류시장 진입 완화</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41132&cntntsId=239087" title="학자금 상환유예">학자금 상환유예</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41133&cntntsId=239088" title="체납액 특례제도">체납액 특례제도</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41134&cntntsId=239089" title="납세자 세금신고">납세자 세금신고</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2460&cntntsId=7786" title="전자(세금)계산서/현금영수증/신용카드">전자(세금)계산서/현금영수증/신용카드</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2460&cntntsId=7786" title="전자(세금)계산서">전자(세금)계산서</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2460&cntntsId=7786" title="개요 및 추진배경">개요 및 추진배경</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2461&cntntsId=7787" title="발급의무대상자">발급의무대상자</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2462&cntntsId=7788" title="발급방법 및 발급절차">발급방법 및 발급절차</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2463&cntntsId=7789" title="발급시기 및 발급∙전송기한">발급시기 및 발급∙전송기한</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2464&cntntsId=7790" title="혜택과 가산세">혜택과 가산세</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2465&cntntsId=7791" title="수정세금계산서 발급방법">수정세금계산서 발급방법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2466&cntntsId=7792" title="주요 세법 개정 내용">주요 세법 개정 내용</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=12363&bbsId=30617" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=12364&bbsId=30675" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=12365&bbsId=30676" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6671&bbsId=50665" title="동영상자료실">동영상자료실</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2468&cntntsId=7793" title="현금영수증∙신용카드">현금영수증∙신용카드</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2468&cntntsId=7793" title="개요 및 결제 흐름도">개요 및 결제 흐름도</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2469&cntntsId=7794" title="발급∙수취시 혜택">발급∙수취시 혜택</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2470&cntntsId=7795" title="가맹점가입">가맹점가입</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2471&cntntsId=7796" title="현금영수증발급의무">현금영수증발급의무</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2472&cntntsId=7797" title="발급거부(미발급)신고">발급거부(미발급)신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41107&cntntsId=239078" title="현금영수증 모바일카드">현금영수증 모바일카드</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2473&cntntsId=7798" title="현금거래확인신청 및 주택임차료 신고">현금거래확인신청 및 주택임차료 신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2475&cntntsId=7799" title="사업용 신용카드 개요">사업용 신용카드 개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2476&cntntsId=7800" title="신용카드결제거부 및 위장가맹점 신고">신용카드결제거부 및 위장가맹점 신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40683&cntntsId=239036" title="결제대행업체 거래시 주의사항">결제대행업체 거래시 주의사항</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=15559&bbsId=30629" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6668&bbsId=30050" title="주요서식">주요서식</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=6670&bbsId=30052" title="참고자료실">참고자료실</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40029&bbsId=50669" title="동영상자료실">동영상자료실</a>
											</li>
										</ul>
									</li>
								</ul>
								<li><a href="#?mi=40250" title="전자기부금영수증 제도">전자기부금영수증 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40251&cntntsId=238907" title="제도 안내">제도 안내</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40252&cntntsId=238908" title="전자기부금영수증 발급 시스템 운영">전자기부금영수증 발급 시스템 운영</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40253&bbsId=50691" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40254&bbsId=50692" title="자주 묻는 질문">자주 묻는 질문</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41102&cntntsId=239068" title="전자송달 제도">전자송달 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41102&cntntsId=239068" title="제도 안내">제도 안내</a>
										</li>
									</ul>
								</li>
								<li><a href="#?mi=40533" title="가업승계 세무컨설팅">가업승계 세무컨설팅</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40594&cntntsId=239010" title="제도안내">제도안내</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40595&cntntsId=239011" title="신청 방법 및 대상자 선정">신청 방법 및 대상자 선정</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40599&bbsId=50796" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40593&bbsId=50793" title="동영상자료실">동영상자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41093&cntntsId=239070" title="소득세 공제감면 컨설팅 제도">소득세 공제감면 컨설팅 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41093&cntntsId=239070" title="제도 안내">제도 안내</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41094&cntntsId=239071" title="신청방법 및 혜택">신청방법 및 혜택</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2498&cntntsId=7809" title="법인세 공제감면 컨설팅 제도">법인세 공제감면 컨설팅 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2498&cntntsId=7809" title="제도 안내">제도 안내</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2499&cntntsId=7810" title="신청방법 및 혜택">신청방법 및 혜택</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40543&bbsId=50768" title="주요서식 작성요령/사례 ">주요서식 작성요령/사례 </a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41121&bbsId=50855" title="동영상자료실">동영상자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="#?mi=40623" title="과세정보 사전수요/ 비밀유지 확인 컨설팅">과세정보 사전수요/ 비밀유지 확인 컨설팅</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40584&cntntsId=239005" title="과세정보 사전 수요 컨설팅">과세정보 사전 수요 컨설팅</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40584&cntntsId=239005" title="제도 안내">제도 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40585&cntntsId=239006" title="신청방법">신청방법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40586&cntntsId=239007" title="사전 수요 컨설팅 제공">사전 수요 컨설팅 제공</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40625&cntntsId=239016" title="비밀유지 확인 컨설팅">비밀유지 확인 컨설팅</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40625&cntntsId=239016" title="제도안내">제도안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40626&cntntsId=239017" title="신청방법">신청방법</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40627&cntntsId=239018" title="비밀유지 사전 확인 컨설팅 제공">비밀유지 사전 확인 컨설팅 제공</a>
											</li>
										</ul>
									</li>
								</ul>
								<li><a href="#?mi=40030" title="착한임대인 세액공제 제도">착한임대인 세액공제 제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40005&cntntsId=238883" title="소개">소개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40041&cntntsId=238889" title="핵심 가이드">핵심 가이드</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40255&bbsId=50693" title="주요서식 작성요령/사례">주요서식 작성요령/사례</a>
										</li>
										<li><a href="/comm/nttFileDownload.do?fileKey=2daacbc878d6b3b17221d15c96735dc1&mi=40368" title="세액공제 계산">세액공제 계산</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40006&bbsId=50671" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40007&bbsId=50670" title="자주 묻는 질문">자주 묻는 질문</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40031&bbsId=50672" title="카드뉴스/리플릿">카드뉴스/리플릿</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40302&bbsId=50695" title="동영상자료실">동영상자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="#?mi=40369" title="가상자산소득 과세제도">가상자산소득 과세제도</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40370&cntntsId=238935" title="가상자산소득 과세 개요">가상자산소득 과세 개요</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40370&cntntsId=238935" title="거주자의 가상자산소득 과세 개요">거주자의 가상자산소득 과세 개요</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40371&cntntsId=238936" title="비거주자의 가상자산소득 과세 개요">비거주자의 가상자산소득 과세 개요</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40372&cntntsId=238937" title="가상자산사업자 거래자료 제출">가상자산사업자 거래자료 제출</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40400&bbsId=50734" title="주요서식">주요서식</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40386&bbsId=50720" title="참고자료실">참고자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="#?mi=40346" title="소득자료 제출 안내">소득자료 제출 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40347&cntntsId=238923" title="실시간 소득파악 제도 안내">실시간 소득파악 제도 안내</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40348&cntntsId=238924" title="소득자료별 제출안내">소득자료별 제출안내</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40348&cntntsId=238924" title="일용근로소득지급명세서">일용근로소득지급명세서</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40349&cntntsId=238925" title="간이지급명세서(거주자의 사업소득)">간이지급명세서(거주자의 사업소득)</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40677&cntntsId=239031" title="간이지급명세서(거주자의 기타소득)">간이지급명세서(거주자의 기타소득)</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40678&cntntsId=239032" title="간이지급명세서(근로소득)">간이지급명세서(근로소득)</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40350&cntntsId=238926" title="사업장제공자 등의 과세자료">사업장제공자 등의 과세자료</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40990&cntntsId=239045" title="소득자료별 제출방법 및 유의사항">소득자료별 제출방법 및 유의사항</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40990&cntntsId=239045" title="소득자료 제출방법 등">소득자료 제출방법 등</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40991&cntntsId=239046" title="성실제출 혜택 및 불성실 제출시 불이익">성실제출 혜택 및 불성실 제출시 불이익</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41003&cntntsId=239047" title="소득자료 제출 시 유의사항">소득자료 제출 시 유의사항</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40994&bbsId=50823" title="소득자료 제출 Q&amp;A">소득자료 제출 Q&amp;A</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40313&bbsId=50712" title="주요서식">주요서식</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40312&bbsId=50713" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=40314&bbsId=50714" title="동영상자료실">동영상자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41085&cntntsId=239067" title="명의도용 안심차단 서비스 안내">명의도용 안심차단 서비스 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41085&cntntsId=239067" title="제도안내">제도안내</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41087&bbsId=50844" title="자주 묻는 질문">자주 묻는 질문</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41088&bbsId=50845" title="주요서식">주요서식</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=41089&bbsId=50846" title="참고자료실">참고자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2510&cntntsId=7817" title="국제조세정보">국제조세정보</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2510&cntntsId=7817" title="해외동향 및 세무정보">해외동향 및 세무정보</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2510&cntntsId=7817" title="외국 세무정보">외국 세무정보</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2511&cntntsId=7818" title="OECD∙UN 발간자료">OECD∙UN 발간자료</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40303&cntntsId=238912" title="해외정보 조회안내">해외정보 조회안내</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2513&cntntsId=7819" title="국제조세 주요 신고제도">국제조세 주요 신고제도</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2513&cntntsId=7819" title="해외금융계좌 신고">해외금융계좌 신고</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2514&cntntsId=7820" title="국제거래정보 통합보고서">국제거래정보 통합보고서</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2515&cntntsId=7821" title="국외전출자 주식등 양도소득세">국외전출자 주식등 양도소득세</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=41123&cntntsId=239079" title="해외신탁신고">해외신탁신고</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2516&bbsId=1103" title="조세조약 및 법령정보">조세조약 및 법령정보</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2520&cntntsId=7822" title="자금출처확인서 발급안내">자금출처확인서 발급안내</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=13452&bbsId=131012" title="발간책자">발간책자</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2522&bbsId=30061" title="참고자료실">참고자료실</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2521&bbsId=30060" title="주요서식">주요서식</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2491&cntntsId=8086" title="명의신탁주식 실소유자 확인안내">명의신탁주식 실소유자 확인안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2491&cntntsId=8086" title="제도 안내">제도 안내</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=17206&bbsId=30670" title="주요서식">주요서식</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=17225&bbsId=30671" title="참고자료실">참고자료실</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2565&cntntsId=7853" title="조세소송">조세소송</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2526&cntntsId=7823" title="세법해석 질의 안내">세법해석 질의 안내</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2526&cntntsId=7823" title="세법해석 질의 안내">세법해석 질의 안내</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2526&cntntsId=7823" title="세법해석 질의 안내">세법해석 질의 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2527&cntntsId=7824" title="신청시 유의사항">신청시 유의사항</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2528&cntntsId=7825" title="세법단순상담 및 세무관련고충 민원처리안내">세법단순상담 및 세무관련고충 민원처리안내</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2530&cntntsId=7826" title="서면질의제도">서면질의제도</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2530&cntntsId=7826" title="서면질의제도 안내">서면질의제도 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2531&cntntsId=7827" title="신청서식 및 작성예시">신청서식 및 작성예시</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2532&cntntsId=7828" title="처리부서 안내">처리부서 안내</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2536&cntntsId=7830" title="세법해석 사전답변제도">세법해석 사전답변제도</a>
											<ul class="depth4">
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2536&cntntsId=7830" title="세법해석 사전답변제도 안내">세법해석 사전답변제도 안내</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2537&cntntsId=7831" title="신청서식 및 작성예시">신청서식 및 작성예시</a>
												</li>
												<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2538&cntntsId=7832" title="처리부서 안내">처리부서 안내</a>
												</li>
											</ul>
										</li>
										<li><a href="/comm/nttFileDownload.do?fileKey=9bd03fa9e354c7b0871536f30ebda388&mi=2539" title="신청∙답변대상이 아닌 사례">신청∙답변대상이 아닌 사례</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=16358&bbsId=30667" title="자주묻는질문">자주묻는질문</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/ad/nf/nltFormatApiList.do?mi=40178" title="세무서식">세무서식</a>
								</li>
								<li><a href="#?mi=2545" title="통합자료실">통합자료실</a>
									<ul class="depth3">
										<li><a href="/nts/na/ntt/selectNttList.do?mi=7133&bbsId=1083" title="국세청 발간책자">국세청 발간책자</a>
											<ul class="depth4">
												<li><a href="/nts/na/ntt/selectNttList.do?mi=7133&bbsId=1083" title="개정세법해설">개정세법해설</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=135770&bbsId=1143" title="분야별해설 책자">분야별해설 책자</a>
												</li>
												<li><a href="/nts/na/ntt/selectNttList.do?mi=40298&bbsId=50696" title="세금안내 책자">세금안내 책자</a>
												</li>
											</ul>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2544&bbsId=1099" title="국세청 프로그램">국세청 프로그램</a>
										</li>
										<li><a href="https://taxlaw.nts.go.kr/st/USESTJ001M.do" target="_blank" title="세무용어사전(새창으로 이동됩니다.)" >세무용어사전</a>
										</li>
										<li><a href="/nts/ad/taxSchdul/selectList.do?mi=135747" title="세무일정">세무일정</a>
										</li>
									</ul>
								</li>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13447&amp;cntntsId=8663" title="정보공개" style='text-decoration:none; cursor:default'>정보공개</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13447&amp;cntntsId=8663" title="정보공개">정보공개</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13447&cntntsId=8663" title="정보공개제도 안내">정보공개제도 안내</a>
										</li>
										<li><a href="/nts/pdoc/openApi/list.do?mi=6409" title="정보목록">정보목록</a>
										</li>
										<li><a href="https://www.open.go.kr" target="_blank" title="정보공개 청구(새창으로 이동됩니다.)" >정보공개 청구</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=6411&bbsId=1075" title="일반행정정보">일반행정정보</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=6413&bbsId=1067" title="예산현황">예산현황</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/ad/od/openDataList.do?mi=6679" title="사전정보공표">사전정보공표</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6685&cntntsId=8097" title="고액 상습체납자 등 명단 공개">고액 상습체납자 등 명단 공개</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6685&cntntsId=8097" title="고액 상습체납자 명단 공개">고액 상습체납자 명단 공개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6686&cntntsId=8098" title="조세포탈범 명단 공개">조세포탈범 명단 공개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=40981&cntntsId=239041" title="세금계산서 발급의무 등 위반자 명단공개">세금계산서 발급의무 등 위반자 명단공개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6687&cntntsId=8099" title="해외금융계좌 고액 신고 의무 위반자 명단 공개">해외금융계좌 고액 신고 의무 위반자 명단 공개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=135731&cntntsId=8101" title="불성실기부금수령단체 명단 공개">불성실기부금수령단체 명단 공개</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6690&cntntsId=8102" title="공공데이터 제공">공공데이터 제공</a>
								</li>
								<li><a href="/nts/na/ntt/selectNttList.do?mi=6691&bbsId=1138" title="정책 실명제">정책 실명제</a>
								</li>
								<li><a href="https://www.prism.go.kr/homepage" target="_blank" title="정책연구보고서(새창으로 이동됩니다.)" >정책연구보고서</a>
								</li>
								<li><a href="https://tasis.nts.go.kr" target="_blank" title="국세통계포털(새창으로 이동됩니다.)" >국세통계포털</a>
								</li>
							</ul>
						</li>
						<li><a href="#?mi=6731" title="국세청 소개" style='text-decoration:none; cursor:default'>국세청 소개</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6729&cntntsId=8131" title="국세청안내">국세청안내</a>
									<ul class="depth3">
										<li><a href="https://call.nts.go.kr/call/cm/cntnts/cntntsView.do?mi=2074&cntntsId=7041" target="_blank" title="대표상담전화(새창으로 이동됩니다.)" >대표상담전화</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6732&cntntsId=8133" title="연혁">연혁</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6738&cntntsId=8139" title="국세청 상징">국세청 상징</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6740&cntntsId=8140" title="조직과 기능">조직과 기능</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6748&cntntsId=8148" title="국세청에서 하는 일">국세청에서 하는 일</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6750&cntntsId=8149" title="열린국세청">열린국세청</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6755&cntntsId=8154" title="차장 소개">차장 소개</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6756&cntntsId=8155" title="역대 청장 소개">역대 청장 소개</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6758&cntntsId=8156" title="국세공무원 소개">국세공무원 소개</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6758&cntntsId=8156" title="국세공무원이란">국세공무원이란</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6759&cntntsId=8157" title="국세청공무원행동강령">국세청공무원행동강령</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/taxSrch/taxSrchPage.do?mi=6761" title="전국 세무관서">전국 세무관서</a>
									<ul class="depth3">
										<li><a href="/nts/taxSrch/taxSrchPage.do?mi=6761" title="지역으로 찾기">지역으로 찾기</a>
										</li>
										<li><a href="/nts/imArea/selectImAreaNmList.do?mi=6762" title="이름으로 찾기">이름으로 찾기</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6767&cntntsId=8163" title="찾아오시는 길">찾아오시는 길</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13322&cntntsId=8648" title="인천공항 납세지원센터">인천공항 납세지원센터</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13322&cntntsId=8648" title="민원증명 신청">민원증명 신청</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13323&cntntsId=8649" title="각종 신고서 접수">각종 신고서 접수</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13324&cntntsId=8650" title="각종 신청 접수">각종 신청 접수</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13325&cntntsId=8651" title="기타 이용가능 업무">기타 이용가능 업무</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=13329&cntntsId=8652" title="인천국제공항 비즈니스센터 운영">인천국제공항 비즈니스센터 운영</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=15630&bbsId=30665" title="자주묻는 질문 답변">자주묻는 질문 답변</a>
										</li>
									</ul>
								</li>
								<li><a href="https://teht.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/ca/e/c/UTECAECA05.xml" target="_blank" title="세무서 민원실 대기인원조회(새창으로 이동됩니다.)" >세무서 민원실 대기인원조회</a>
								</li>
							</ul>
						</li>
						<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6788&cntntsId=8280" title="누리집 안내" style='text-decoration:none; cursor:default'>누리집 안내</a>
							<ul class="depth2">
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6788&cntntsId=8280" title="누리집 이용안내">누리집 이용안내</a>
								</li>
								<li><a href="/nts/nurisitemap.do?mi=6789" title="누리집 안내지도">누리집 안내지도</a>
								</li>
								<li><a href="#?mi=11444" title="납세자별 정보">납세자별 정보</a>
									<ul class="depth3">
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11446&cntntsId=8815" title="개인사업자">개인사업자</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11447&cntntsId=8816" title="법인사업자">법인사업자</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11448&cntntsId=8817" title="신규사업자">신규사업자</a>
										</li>
										<li><a href="/taxpayer_advocate/cm/cntnts/cntntsView.do?mi=11466&cntntsId=8294" target="_blank" title="영세사업자(새창으로 이동됩니다.)" >영세사업자</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11450&cntntsId=8818" title="근로소득자">근로소득자</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=11451&cntntsId=8819" title="부동산소득자">부동산소득자</a>
										</li>
										<li><a href="/nts/na/ntt/selectNttList.do?mi=2516&amp;bbsId=1103" title="해외투자자">해외투자자</a>
										</li>
										<li><a href="/nts/cm/cntnts/cntntsView.do?mi=2364&cntntsId=7741" title="납부안내">납부안내</a>
										</li>
										<li><a href="https://www.hometax.go.kr/websquare/websquare.wq?w2xPath=/ui/pp/index_pp.xml&tmldx=01&tml2lldx=&tm3lldx=" target="_blank" title="사업자상태조회(새창으로 이동됩니다.)" >사업자상태조회</a>
										</li>
										<li><a href="https://www.hometax.go.kr/websquare/websquare.wq?w2xPath=/ui/pp/index_pp.xml&tmIdx=02&tm2lIdx=&tm3lIdx=" target="_blank" title="민원증명발급(새창으로 이동됩니다.)" >민원증명발급</a>
										</li>
									</ul>
								</li>
								<li><a href="/nts/itp/policy/policyInfo.do?mi=6790" title="개인정보처리방침">개인정보처리방침</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=6791&cntntsId=8169" title="저작권정책">저작권정책</a>
								</li>
								<li><a href="/nts/cm/cntnts/cntntsView.do?mi=17455&cntntsId=8803" title="읽기 전용 프로그램">읽기 전용 프로그램</a>
								</li>
								<li><a href="/nts/bannerNtsListAll.do?mi=40685" title="배너모음">배너모음</a>
								</li>
							</ul>
						</li>
					<!--END-->

</ul>	
			</div>
			
		</div>
	</header>
<div id="wrap">    
		
	        <div id="container_m" class="container">
	            <!-- 좌측메뉴 -->
	            <!--START-->
<input type="hidden" id="leftCurrMi" value="6720">
<input type="hidden" id="tabBaseMi" value="6720">
<input type="hidden" id="tabUpperMi" value="">
<input type="hidden" id="tabUpperMenu" value="">
<nav id="snb">
<h2><a href="/nts/ad/cntnts/cntntsView.do?mi=13366"  title="국민소통">국민소통</a></h2>
	<ul class="depth2">
		<li><a data-id="13366" href="/nts/ad/cntnts/cntntsView.do?mi=13366"  title="국세청100배 활용하기 가이드맵">국세청100배 활용하기 가이드맵</a>
				</li>
		<li><a data-id="6713" href="/nts/cm/cntnts/cntntsView.do?mi=13346&cntntsId=8654"  title="규제혁신">규제혁신</a>
			<ul class="depth3">
				<li><a id="13346" href="/nts/cm/cntnts/cntntsView.do?mi=13346&cntntsId=8654"  title="규제혁신 신문고">규제혁신 신문고</a>
				</li>
				<li><a id="6714" href="/nts/cm/cntnts/cntntsView.do?mi=6714&cntntsId=8121"  title="규제혁신 과제현황">규제혁신 과제현황</a>
				</li>
				<li><a id="6715" href="/nts/cm/cntnts/cntntsView.do?mi=6715&cntntsId=8122"  title="심사중인 규제법안">심사중인 규제법안</a>
				</li>
				<li><a id="6716" href="/nts/cm/cntnts/cntntsView.do?mi=6716&cntntsId=8123"  title="부처별 보도자료">부처별 보도자료</a>
				</li>
				<li><a id="6717" href="/nts/cm/cntnts/cntntsView.do?mi=6717&cntntsId=8124"  title="규제법령 정보">규제법령 정보</a>
				</li>
				<li><a id="13347" href="/nts/cm/cntnts/cntntsView.do?mi=13347&cntntsId=8655"  title="규제입증 요청">규제입증 요청</a>
				</li>
			</ul>
		</li>
		<li class="active"><a data-id="6719" href="/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126"  title="적극행정">적극행정</a>
			<ul class="depth3">
				<li class="active"><a id="6720" href="/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126"  title="제도소개">제도소개</a>
				</li>
				<li><a id="6721" href="https://www.mpm.go.kr/proactivePublicService/activeRecommand/recommendation"  rel="noopener noreferrer" target="_blank" title="적극행정 국민추천(새창으로 이동됩니다.)">적극행정 국민추천</a>
				</li>
				<li><a id="6722" href="https://www.epeople.go.kr/nep/pttn/negativePttn/NegativePttnCotents.npaid"  rel="noopener noreferrer" target="_blank" title="소극행정 신고(새창으로 이동됩니다.)">소극행정 신고</a>
				</li>
				<li><a id="6724" href="https://www.mpm.go.kr/proactivePublicService/local/localNotice"  rel="noopener noreferrer" target="_blank" title="적극행정 자료실(새창으로 이동됩니다.)">적극행정 자료실</a>
				</li>
			</ul>
		</li>
		<li><a data-id="132011" href="/taxpayer_advocate/main.do?mi=132011"  rel="noopener noreferrer" target="_blank" title="납세자권익 24(새창으로 이동됩니다.)">납세자권익 24</a>
			</li>
		</ul>
<div class="snb_imgbox">
	<a href="https://call.nts.go.kr/call/main.do" target="_blank" title="국세상담센터 상담안내 바로가기(새창)">
		<p class="tit"><span>국세상담센터</span><img src="/images/web/nts/layout/snb_126.png" alt="126"></p>
		<p class="txt">국세관련 모든 상담은 국번없이 126<br>전국 어디서나 편리하게 상담받으세요.</p>
		<p class="time">평일 9시~18시 <span>(탈세제보는 24시간)</span></p>
	</a>
</div>
	</nav>
<!--END-->


<!-- // 좌측메뉴 -->
	            <!-- CONTAINER -->
	            <div id="container">
	            	<div class="title_area">
						<h2 class="titleH2">제도소개</h2>
			<div class="locationWrap">
				<ul class="location">
					<li><a href="/nts/main.do" class="home">홈</a></li>
					<li><a href='/nts/ad/cntnts/cntntsView.do?mi=13366'>국민소통</a></li><li><a href='/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126'>적극행정</a></li><li><a href='/nts/cm/cntnts/cntntsView.do?mi=6720&cntntsId=8126'>제도소개</a></li></ul>
				<ul class="shareWrap">
					<li><a href="#shareList" class="share hashToggle" title="공유하기"><span class="sr-only">공유하기</span></a>
						<ul id="shareList">
							<li><a href="javascript:;" class="facebook" onclick="faceLink();" title="페이스북 공유하기 새창열림"><span class="sr-only">페이스북</span></a></li>
							<li><a href="javascript:;" class="twitter" onclick="twitterLink();" title="트위터 공유하기 새창열림"><span class="sr-only">트위터</span></a></li>
							<li><a href="javascript:;" class="kakaostory" onclick="kakaostoryLink();" title="카카오스토리 공유하기 새창열림"><span class="sr-only">카카오스토리</span></a></li>
						</ul>
					</li>
					<li><a href="javascript:;" class="print btnPrint" data-sysid="nts" title="인쇄 새창열림"><span class="sr-only">인쇄</span></a></li>
				</ul>
			</div></div>
	                <!-- CONTENTS -->
	                <div id="contents">
						<!--START-->
										<!--END-->

	









	
	
		<div class="bbs_FaqA_custom">
                                <ul class="bbs_FaqA">
                                    <li class="faq">
                                        <a href="#none" title="질문">Do I have to file a return?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>Principally, a resident is any individual who has his/her domicile in Korea or a place of residence for 1 year or more in Korea. The domicile shall be judged by the objective facts of living relationship, such as the existence of a family living together in Korea and of the property located in Korea. And, the 'place of residence' means the place where a person has dwelt for a long time besides his address, and in which no close general living relationship is formed as the domicile.</p>
                                        <p class="p_mgt">A taxpayer who falls within the following cases is deemed to have a domicile in Korea.</p>
                                        <p>ⅰ) Who has an occupation which would require him to reside in Korea for 1 year or more; or<br>
                                            ⅱ) Who has his family in Korea and is likely to reside in Korea for 1 year or more based on his occupation or assets held in Korea.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">How do I know if I am a Korean resident?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                        <p> If you are a foreigner resident for the entire year, you have to file a final tax return in the same way as a Korean resident does. Four major types of individual income consisting of global income, retirement income, capital gains and timber income are all taxable.</p>
                                        <p class="p_mgt">Furthermore, if you maintain a business place(usually termed as a “permanent establishment” in tax conventions) in Korea or have only real estate income arising from Korean sources without maintaining PE, you must also file a tax return even though your status is considered to be non-resident.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">When do I have to file?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                        <p>The regular return period for the income accruing for the tax year concerned begins on May 1 and ends on May 31 of the next year. For tax purposes, individual taxpayers must use a calendar year as their taxable year. When the due date for filing a return and paying tax falls on Sunday or a legal holiday, the next business day is the due date</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">Where do I file and pay?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                        <p>You have to file your return to the district tax office(DTO) having jurisdiction over your domicile. But your tax return filed at an unqualified DTO will be automatically transferred to the relevant DTO that has jurisdiction on your current domicile. And then, you can pay your tax at any bank or post offices by May 31. You may also use electronic payment system by phone (phone banking; ARS) or internet (internet banking; refer to National Tax Electronic Payment banner on www.nts.go.kr) at your home.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">Could you explain the income tax rates in Korea? (in the case of business income earner)<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>The amount of income tax on global income is calculated by applying increasing marginal tax rates to respective tax base, and may be determined by using the following table.</p>
                                            <div class="tbl_st2">
                                                <table>
                                                    <caption>The taxable income is the total amount of wage and salary income remaining after the deduction of the following amount (&#8361;80,000 per day for a daily worker)</caption>
                                                    <colgroup>
                                                        <col span="2" style="width:50%;">
                                                    </colgroup>
                                                    <thead>
                                                        <tr>
                                                            <th scope="col">Tax Base of Global Income</th>
                                                            <th scope="col">Tax Rates</th>
                                                          </tr>
                                                    </thead>
                                                    <tbody>
                                                          <tr>
                                                            <td>Less than &#8361;10,000,000</td>
                                                            <td>8% of tax rate</td>
                                                          </tr>
                                                          <tr>
                                                            <td>&#8361;10,000,000 ~ &#8361;40,000,000</td>
                                                            <td>&#8361;800,000 + 17% of the amount over &#8361;10,000,000</td>
                                                          </tr>
                                                          <tr>
                                                            <td>&#8361;40,000,000 ~ &#8361;80,000,000</td>
                                                            <td>&#8361;5,900,000 + 26% of the amount over &#8361;40,000,000</td>
                                                          </tr>
                                                          <tr>
                                                            <td>Over &#8361;80,000,000</td>
                                                            <td>&#8361;16,300,000 + 35% of the amount over &#8361;80,000,000</td>
                                                          </tr>
                                                    </tbody>
                                                </table>
                                            </div>  
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">What is the scope of persons eligible for Personal Exemptions for the income tax purpose?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>Persons eligible for spousal exemption, dependent exemption, or exemption for handicapped or aged persons must be (i) a spouse and/or unmarried lineal descendant and (ii) family members who are listed on the registration card of the resident actually living at the domicile or residence.</p>
                                           <p class="p_mgt">A person who has temporarily left the taxpayer's domicile or residence for reasons of schooling, medical treatment, business, or work may still be entitled to an exemption. The determination of eligibility shall be made based on the existing conditions at the closing date of the tax period concerned.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">Do I have to report foreign income?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>If you are a Korean resident, you have to report your income from all sources, both inside and outside Korea. You also should report foreign income in Korean Won and use the exchange rate that was in effect on the day you received the income.</p>
                                            <p class="p_mgt">Generally, when you report such foreign income on your return, you can take either a deduction or a credit for income taxes imposed on the income by a foreign country. Tax treaties with other countries may affect whether you are eligible for this credit.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">How much tax do I have to pay on income earned from a foreign company located overseas?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>Your income earned from a foreign company is not treated differently from the Korean sourced income. However, you may take either a deduction or a credit for income taxes imposed on you by the foreign government when you file a final tax return on your global income.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">Is there any credit for tax paid in foreign countries?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>Where a resident has paid or is to pay income tax in a foreign country, the tax amount paid or payable is deducted from the amount of Korean income tax accrued with a limit. This limit is an amount equivalent to that of the income tax owed without the application of this credit, multiplied by the ratio of income from foreign sources to total taxable income. If the foreign tax amount paid or payable exceeds this limit, the excess portion may be carried over for 5 years.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">When can I expect my refund?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>When you complete your tax return, you get to know if you already paid more income tax than you have to. If so, you can get a refund of the amount you overpaid. Normally, the refund process for the returns filed takes at least 4 weeks and can be done during June.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">Can the tax losses be carried forward to offset future profits?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>The amount of losses incurred during each business year within the five year prior to the first day of the current business year which were not thereafter deducted in the calculation of the basis for assessment of taxes shall be deducted from the income of a domestic corporation for business year. The amount of losses of a domestic corporation for each business year shall be the total amount of earning during the business year deducted from the total amount of losses incurred during the business year.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">Which form should I use?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>There are 2 forms you can choose when you file your final tax return: Form 40-1 and Form 40-4. You should use Form 40-4 if you have only either business income or real estate income. For details, refer to the information on the first page of Form 40-4. You should use Form 40-1 otherwise.<p class="p_mgt">Also, where a corporation has failed to submit a payment statement or where the details of transactions submitted by the company are found to be unclear, an amount equivalent to 2% of the amount of the transactions in the reports not submitted or unclear is assessed as penalty tax.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">What happens after I file?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>When we receive your return, we usually review it based on the information you provided. However, we may select your return for a more detailed review before we assess it. If so, and we ask you to give us documents to verify the deductions or credits you claimed, your assessment may be delayed. We also review some returns after we have assessed them, to verify the income reported or the deductions or credits claimed.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">What records should I keep?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>You must keep records so that you can prepare a complete and accurate income tax return. The law does not require any special form of records. However, you should keep all receipts, cancelled checks or other proofs of payments, and any other records to support any deductions or credits you claim. For assessment of tax you owe, generally you should keep these records for 5 years from the date you filed the return.</p>
                                        </div>
                                    </li>
                                    <li class="faq">
                                        <a href="#none" title="질문">What penalties do I pay?<span class="faq_arr"></span></a>
                                        <div class="faq_A" title="답변" style="display: none;">
                                            <p>The penalty for both failure-to-return and failure-to-pay is assessed if a return or payment is not accomplished by the due date.</p>
                                            <p class="p_mgt"><span class="font_FB">Penalty on Failure to File Returns</span><br> If a resident either fails to file a tax return or under-reports the relevant income, an amount equivalent to 20% of the income unreported or under-reported will be included in the calculation of tax amount as follows:</p>
                                            <div class="box_st1 rsp_img ac">
                                                <img src="/images/web/english/sub/img522.png" alt=" Proper Income Amount to be reported/Income Amount un(under)reported × Tax Amount Properly Calculated × 20%">
                                            </div>
                                            <p class="p_mgt"><span class="font_FB">Penalty on Non-payment or Underpayment of Tax</span><br>When the income tax payable is not paid properly, a penalty in the amount of 0.03% of the amount shall be added to the amount of tax due, for each day the amount remains unpaid.</p>
                                        </div>
                                    </li>
                                </ul>
                            </div>
                        </div>
		
		<script>
			$(function() {
				$('a').on('click', function() {
					if($(this).prop('href').indexOf('/comm/ntsFileDown.do') > -1) {
						$(this).prop('href', decodeURI($(this).prop('href')));
						$(this).prop('href', encodeURI($(this).prop('href')));
					}
				});
			});
			
			function fn_popupOpen(url, pName, width, height, left, top) {

				width = window.screen.width;
				height = window.screen.height;

				window.open(url, "openPopEvent", 'width=' + width + ', ' + 'height='
						+ height + ',left=0, top=0, resizable= yes, scrollbars=no, toolbar=no ,location=no, directories=no'
						+ ',status=no,menubar=no,copyhistory=no');
			}
			
			// 콘텐츠 업로드 파일 미리보기 or 다운로드
			function viewOrDown(id){
				if (id != null && id != "") {
					$.ajax({
						type : "post",
						url : "/comm/cntnts/systemCheck.do",
						dataType : "json",
						success : function(data) {
							var sendUrl = "/comm/fileDownload.do?fileKey=" + id;
							
							var synapViewerAt = data.synapViewerAt;
							var filepathIp = data.filepathIp;
							var transIp = data.transIp;
							
							if (synapViewerAt != "" && synapViewerAt == "Y" && filepathIp != "" && transIp != "") {
								sendUrl = transIp + "/SynapDocViewServer/job?fileType=URL&convertType=0&filePath=" + filepathIp + "/comm/fileDownload.do?fileKey=" + id + "&fid=cntnts" + id + id + id + id;	
							}
							
							window.open(sendUrl, "docTransName");
						},
						error : function(data) {
							alert("오류가 발생하였습니다.\n관리자에게 문의하세요.");
						}		
					});			
				} else {
					alert("파일을 확인해주세요.");
					return false;
				}
			}	
			
			$(function() {
				$('.VocIframe2').on('click',function(){						
					var voc2 = $('#iframe_Voc_2').attr('src');
					if(voc2 == ''){
						document.getElementById('iframe_Voc_2').src = "https://www.epeople.go.kr/frm/pttn/openPttnList.npaid?frmMenuMngNo=WBF-1009-000021";
					}
				});
				$('.VocIframe3').on('click',function(){
					var voc3 = $('#iframe_Voc_3').attr('src');
					if(voc3 == ''){
						document.getElementById('iframe_Voc_3').src = "https://www.epeople.go.kr/frm/pttn/pttnRqstInfo.npaid?frmMenuMngNo=WBF-0606-000138";
					}					
				});	
			});
		</script>
	

</div>
	                <!-- // CONTENTS -->
	            </div>
	            <!-- // CONTAINER -->
	            


<script>
	//만족도 조사 ( 엔터 )
	$(function(){
		$('#etcOpinion').keypress(function(event){
			if ( event.which == 13 ) {
				$('.csnstSubmit').click();
			}	
		});
			
	});
	
	$(document).on('click','.csnstSubmit',function(){
		/* 20/01/02 담당자 요청으로 제거
		if(!confirm('만족도 조사에 참여하시겠습니까?')){
			return false;
		} else {

		}
		*/
		
		if ($("input[name='stsfdgEvlScore']:checked").val() == null) {
			alert("만족도 항목을 선택해주세요.");
			return false;
		} 
		
		var data = $("#csnstForm").serialize();
		
		$.ajax({
			type: "POST",
			datatype:"json",
			data: data,
			url: "/nts/cs/csnst/insertCsnstInfo.do",
			success:function(result){
				var retValue = result;
				if(retValue == 1){
					alert("만족도 참여를 완료하였습니다.");
				} else if(retValue == 2){
					alert("하루에 1회만 참여할 수 있습니다.");
				} else {
					alert("만족도 참여에 실패하였습니다.");
				}
			},
			error:function(data) {   
				alert("오류가 발생하였습니다.\n관리자에게 문의하세요.");
			}
					
		});		
	});
</script>								
								<!-- 만족도조사 -->
						        <div class="satisfaction"> 
						            <h3 class="hid">콘텐츠 만족도 조사</h3>
						            <p class="question">  페이지에서 제공하는 정보에 대하여 만족하셨습니까?  </p>
						            <form name="csnstForm" id="csnstForm" method="post" >
						                <fieldset>
						                    <legend>만족도 조사</legend>
						                    <input type="hidden" name="sysId" id="csnstSysId" value='nts'>
						                    <input type="hidden" name="menuId" id="csnstMenuId" value="6720">
						                    <div class="satisfaction_list">
						                        <div class="input_radio">
						                            <span><input name="stsfdgEvlScore" value="5" id="stsfdgEvlScore1" type="radio">
						                            <label for="stsfdgEvlScore1">매우만족</label></span>
						                            <span><input name="stsfdgEvlScore" value="4" id="stsfdgEvlScore2" type="radio">
						                            <label for="stsfdgEvlScore2">만족</label></span>
						                            <span><input name="stsfdgEvlScore" value="3" id="stsfdgEvlScore3" type="radio">
						                            <label for="stsfdgEvlScore3">보통</label></span>
						                            <span><input name="stsfdgEvlScore" value="2" id="stsfdgEvlScore4" type="radio">
						                            <label for="stsfdgEvlScore4">불만족</label></span>
						                            <span><input name="stsfdgEvlScore" value="1" id="stsfdgEvlScore5" type="radio">
						                            <label for="stsfdgEvlScore5">매우불만족</label></span>
													<input type="button" value="평가하기" class="csnstSubmit btn_na mini" >
						                        </div>
						                    </div>
						                </fieldset>
						            </form>
						        </div>
						        <!-- //만족도조사 --><!-- 바로가기 -->
	            <div id="quickWrap">
			<h2>
				<a href="#quickWrap" class="hashToggleClass">바로가기</a>
			</h2>
			<ul class="lst">
				<li><a href="https://www.hometax.go.kr" class="font_FB" style="font-size:0.85rem" target="_blank" title="홈택스 바로가기(새창)">홈택스</a></li>
				<li><a href="https://www.youtube.com/@ntskorea" class="font_FB" style="font-size:0.85rem" target="_blank" title="국세청 유튜브 바로가기(새창)">국세청 유튜브</a></li>
				<li><a href="https://call.nts.go.kr/call/main.do" class="font_FB" style="font-size:0.85rem" target="_blank" title="국세상담센터 바로가기(새창)">국세상담센터</a></li>
				<li><a href="https://taxlaw.nts.go.kr" target="_blank" class="font_FB" title="국세법령정보시스템 바로가기(새창)" style="letter-spacing:-0.05rem;  font-size:0.85rem">국세법령정보시스템</a></li>
				<li><a href="https://www.nts.go.kr/museum/main.do" target="_blank" title="국립조세박물관 바로가기(새창)">국립조세박물관</a></li>
				<li><a href="https://tasis.nts.go.kr" target="_blank" title="국세통계포털 바로가기(새창)">국세통계포털</a></li>	
				<li><a href="https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&tmIdx=42&tm2lIdx=4203000000&tm3lIdx=4203010000" class="font_FB" style=" font-size:0.85rem" target="_blank" title="국세환급금 찾기 바로가기(새창)">국세환급금 찾기</a></li>
				<li><a href="https://www.nts.go.kr/taxpayer_advocate/main.do" target="_blank" title="납세자권익24 바로가기(새창)">납세자권익24</a></li>
				<li><a href="https://www.nts.go.kr/nts/ad/nf/nltFormatApiList.do?mi=40178" target="_blank" title="세무서식 바로가기(새창)">세무서식</a></li>
				<li><a href="https://kids.nts.go.kr/kid/main.do" target="_blank" title="어린이 국세청 바로가기(새창)">어린이 국세청</a></li>
				<li><a href="http://www.icl.go.kr" target="_blank" title="취업후 학자금상환 바로가기(새창)">취업후 학자금상환</a></li>				
				<li><a href="https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&tmIdx=47&tm2lIdx=4710000000&tm3lIdx=4710010000" class="font_FB" style=" font-size:0.85rem" target="_blank" title="탈세제보 바로가기(새창)">탈세제보</a></li>
				<li><a href="https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&tmIdx=47&tm2lIdx=4710000000&tm3lIdx=4710090000" class="font_FB" target="_blank" title="부동산 탈세 신고센터 바로가기(새창)">부동산 탈세 신고센터</a></li>
				<li><a href="https://i.nts.go.kr/taxstudy/main.do" target="_blank" title="국세공무원교육원바로가기(새창)">국세공무원교육원</a></li>	
				<li><a href="https://i.nts.go.kr/llsc/main.do" target="_blank" title="주류면허지원센터 바로가기(새창)">주류면허지원센터</a></li>	
				<li><a href="https://i.nts.go.kr/ksuul/main.do" target="_blank" title="K-SUUL 포털 바로가기(새창)">K-SUUL 포털</a></li>
				<li><a href="https://www.nts.go.kr/gmt/main.do" target="_blank" title="글로벌최저한세 포털 바로가기(새창)">글로벌최저한세 포털</a></li>
				
				<li><a href="/nts/taxSrch/taxSrchPage.do?mi=6761" title="지방청·세무서 페이지 바로가기">지방청&middot;세무서</a></li>
				<li><a href="https://taxstudy.nts.go.kr/taxedu/main.do" target="_blank" title="납세자세법교실 바로가기(새창)">납세자세법교실</a></li>								
			</ul>			
			<p class="top">
				<a href="#wrap">맨위로</a>
			</p>
		</div><!-- //바로가기 -->
	        </div>
	        <!-- // CONTAINER 클래스 -->        
	    </div>
	<!-- 검색 -->
	<div id="searchArea" style="display:none;">
		<iframe id="searchFrame" name="searchFrame" src="" style="width: 100%;height:1000px;">
		</iframe>
		
	</div>
	
	<!-- menuForm -->
	<!--공통 메뉴 Form -->
<form name="mainMenuForm" id="mainMenuForm" method="post">
	<input type="hidden" name="mi" id="nowMenuId" value="" />
	<input type="hidden" name="paramNm" id="paramNm" value=""/>
	<input type="hidden" name="paramVal" id="paramVal" value=""/>
</form>
<!--/공통 메뉴 Form -->
	
<script>
$(function() {
	
	//공통 submit
	$(".menuFormBtn").click(function(){
		var paramVal = $(this).attr('data-param'); 
		var paramNm = $(this).attr('data-nm');
		var paramUrl = $(this).attr('data-url');
		$("#paramVal").val(paramVal);
		$("#paramNm").val(paramNm);
		setTrimMenuId();
		$("#mainMenuForm").attr('action', paramUrl).submit();
	});
	
});

//파라미터 페이지 이동 
function goParamPage( setVal, setNm, setUrl ) {
	$("#paramNm").val(setNm);
	$("#paramVal").val(setVal);
	setTrimMenuId();
	$("#mainMenuForm").attr('action', setUrl).submit();
};

//메뉴 아이디 공백제거
function setTrimMenuId(){
	var nowMenuId = $.trim($("#nowMenuId").val());
	$("nowMenuId").val(nowMenuId);
};

</script>
	
	 
	
	

	<!-- FOOTER -->
        <script>
	function stdgOpen(){
		window.open("/nts/si/stdg/insertStdgPage.do", "고객만족도 조사", "width=700, height=820, top=100, left=10, scrollbars=yes, menubar=no, toolbar=no, location=no, status=no");
	}
	
	function typoNotifyOpen(){
		var menuNm = "";
		$(".locationWrap .location li").each(function(){
			menuNm = menuNm + $(this).find("a").text() + " > ";
		});
		if($("#ciMenuId").val() == ''){
			menuNm = "홈 > 메인 > "
		}
		if($("#ciMenuId").val() =='2214'){
			menuNm = "홈 > 알림·소식 > 모범∙아름다운 납세자 > 모범납세자 > "
		}
		if($("#ciMenuId").val() =='2215'){
			menuNm = "홈 > 알림·소식 > 모범∙아름다운 납세자 > 아름다운 납세자 > "
		}
		$("#ciMenuNm").val(menuNm.slice(0, -2));	
// 		$("#ciUrl").val(location.href);
		
		var ciPopup = document.cntntsPopup;
		
		window.open("", "ciPopupView", "width=700, height=410, top=100, left=100, scrollbars=yes, menubar=no, toolbar=no, location=no, status=no");
		ciPopup.action = '/nts/ad/im/insertcntntsImprvmPage.do';
		ciPopup.target = "ciPopupView";
		ciPopup.submit();
	}	
	
</script>
	<form name="cntntsPopup" id="cntntsPopup" method="post" >
		<input type="hidden" name="ciMenuNm" id="ciMenuNm" value="" />
<!-- 		<input type="hidden" name="ciUrl" id="ciUrl" value="" /> -->
		<input type="hidden" name="ciMenuId" id="ciMenuId" value="6720">
	</form>
	<footer id="footer">
		<div class="container">
			<h2><img src="/images/web/nts/layout/logo1.png" alt="국세청"></h2>
			
			<div class="footInfo">
				<address>(우)30128 세종특별자치시 국세청로 8-14 국세청 (정부세종2청사 국세청동)</address>
				<address><a target="_blank" title="상담전화 이용안내 새창열림" href="https://call.nts.go.kr/call/cm/cntnts/cntntsView.do?mi=2074&cntntsId=7041">국세청 대표 상담전화는 전국 어디서나 국번 없이 126번(유료)</a></address>
			</div>
			
			<div class="lstSnsBox">
				<ul class="lst">
					<li><a href="https://www.youtube.com/channel/UCVTdK_EozBDQ7ICMPJdbpzQ" target="_blank" title="국세청 유튜브 바로가기(새창)">	<span class="icons icon5"></span>국세청 유튜브</a></li>
					<li><a href="https://www.instagram.com/nts.korea/" target="_blank" title="국세청 인스타그램 바로가기(새창)">	<span class="icons icon8"></span>국세청 인스타그램</a></li>
					
					<li><a href="http://www.facebook.com/ntsKorea" target="_blank" title="국세청 페이스북 바로가기(새창)"><span class="icons icon2"></span>국세청 페이스북</a></li>
					<li><a href="http://blog.naver.com/ntscafe/" target="_blank" title="국세청 네이버 블로그 바로가기(새창)"><span class="icons icon1"></span>국세청 네이버 블로그</a></li>
					
					<li><a href="https://x.com/ntskorea" target="_blank" title="국세청 X 바로가기(새창)"><span class="icons icon3"></span>국세청 X</a></li>
					<li><a href="https://story.kakao.com/ch/nts" target="_blank" title="국세청 카카오스토리 바로가기(새창)"><span class="icons icon6"></span>카카오스토리</a></li>
					<!-- <li><a href="https://post.naver.com/my.nhn?memberNo=4795084" target="_blank" title="국세청 네이버 포스트 바로가기(새창)"><span class="icons icon4"></span>국세청 네이버 포스트</a></li> -->
					
					</ul>
			</div>
			<div class="protectionLink">
				<a href="/nts/cm/cntnts/cntntsView.do?mi=6788&cntntsId=8280">누리집 이용안내</a>
				<a href="/nts/nurisitemap.do?mi=6789">누리집 안내지도</a>
				<!-- <a href="/nts/cm/cntnts/cntntsView.do?mi=11446&cntntsId=8815">납세자별 정보</a> -->
				<a href="/nts/itp/policy/policyInfo.do?mi=6790"><strong>개인정보처리방침</strong></a>
				<a href="/nts/cm/cntnts/cntntsView.do?mi=6791&cntntsId=8169">저작권정책</a>
				<a href="javascript:stdgOpen()">만족도조사</a>
				<a href="javascript:typoNotifyOpen()">오류오타신고</a>
				<a href="/nts/cm/cntnts/cntntsView.do?mi=17455&cntntsId=8803">읽기 전용 프로그램 안내</a>
			</div>
			<p class="copyright">COPYRIGHT(c) <em>National Tax Service</em>. All Rights Reserved.</p>
			<p class="wa">
				<a href="http://www.wa.or.kr/board/list.asp?BoardID=0006" title="새창열림" target="_blank" id="waPc">
					<img src="/images/web/nts/layout/wa_mark_2026.png" alt="(사)한국장애인단체총연합회 한국웹접근성인증평가원 웹 접근성 우수사이트 인증마크(WA인증마크)">
				</a>
<!-- 					<a href="http://www.wa.or.kr/board/list.asp?BoardID=0006" title="국가 공인 인증기관 : (사)한국장애인단체총연합회 한국웹접근성인증평가원(새창열림)" target="_blank" id="waMb"> -->
<!-- 						<img src="/images/web/nts/layout/wa_mark.png" alt="(사)한국장애인단체총연합회 한국웹접근성인증평가원 웹 접근성 우수사이트 인증마크(WA인증마크)"> -->
<!-- 					</a>					 -->
			</p>
			<p class="top"><a href="#wrap">맨위로</a></p>
		</div>
	</footer><!-- //FOOTER -->
	<!-- /menuForm -->
	<script src="/js/webtrends.js"></script>
	<script>
	// 서브 스타일가이드 관련 JS
	$(function() {
	    $("#con_com_box > div").hide(); // Initially hide all content
	    $("#tabs li:first").attr("id", "current"); // Activate first tab
	    $("#con_com_box > div:first").fadeIn(); // Show first tab content
	
	    $('#tabs a').click(function(e) {
	        $("#con_com_box > div").hide(); //Hide all content
	        $("#tabs li").attr("id", ""); //Reset id's
	        $(this).parent().attr("id", "current"); // Activate this
	        $('#' + $(this).attr('title')).fadeIn(); // Show content for current tab
	    });
	});
	</script>
</body>

</html>
