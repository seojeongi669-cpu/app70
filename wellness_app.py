"""초록하루 · 가족 식사·운동 플래너
실행: streamlit run wellness_app.py
파일: wellness_app.py + requirements.txt
저장: 기본 SQLite는 Cloud 서버 초기화 때 유실 가능. 개인 코드는 비밀번호처럼 보관.
영구 저장 선택: Supabase SQL Editor:
create table public.wellness_accounts (id text primary key,payload jsonb not null,version integer not null default 0);
alter table public.wellness_accounts enable row level security;
-- 공개 접근 정책 추가 금지. 서버 전용 키만 사용.
Streamlit Secrets (GitHub 업로드 금지):
SUPABASE_URL="https://프로젝트.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="서버 전용 키"
KAKAO_REST_API_KEY="선택: Kakao Developers 로컬 API 사용 가능한 REST 키"
지도: 키가 있으면 Kakao Local 키워드 검색으로 동네/반경 검색.
키가 없으면 지도 검색 링크만 제공(가짜 장소 표시 없음).
식품: 내장 메뉴는 일반적인 1회 분량의 교육용 대략값. 제품 영양표 직접 입력 지원.
의료 진단, 섭취 제한, 감량 예측을 제공하지 않음. 미성년자는 체중·소모열량 기능 제한.
"""
import streamlit as st
import streamlit.config as config
import requests,sqlite3,json,secrets,hashlib,html
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
for k,v in {'theme.base':'light','theme.primaryColor':'#39875C','theme.backgroundColor':'#F3F8EF','theme.secondaryBackgroundColor':'#FFFFFF','theme.textColor':'#254B37'}.items(): config.set_option(k,v)
st.set_page_config(page_title='초록하루 · 식사와 운동',page_icon='🌱',layout='centered')
TODAY=datetime.now(ZoneInfo('Asia/Seoul')).date()
def remote():
    try:return bool(st.secrets.get('SUPABASE_URL') and st.secrets.get('SUPABASE_SERVICE_ROLE_KEY'))
    except Exception:return False
def db(key,data=None,version=None):
    if remote():
        root=st.secrets['SUPABASE_URL'].rstrip('/')+'/rest/v1/wellness_accounts'
        headers={'apikey':st.secrets['SUPABASE_SERVICE_ROLE_KEY'],'Authorization':'Bearer '+st.secrets['SUPABASE_SERVICE_ROLE_KEY'],'Prefer':'return=representation'}
        if data is None:
            r=requests.get(root,params={'id':'eq.'+key},headers=headers,timeout=20);r.raise_for_status();rows=r.json()
            return (rows[0]['payload'],rows[0]['version']) if rows else (None,None)
        if version is None:
            r=requests.post(root,headers=headers,json={'id':key,'payload':data,'version':0},timeout=20)
        else:
            r=requests.patch(root,params={'id':'eq.'+key,'version':'eq.'+str(version)},headers=headers,json={'payload':data,'version':version+1},timeout=20)
        r.raise_for_status()
        if not r.json():raise ValueError('다른 화면에서 변경됐어요. 새로고침 후 다시 해 주세요.')
        return
    with sqlite3.connect('wellness_data.sqlite3',timeout=20) as c:
        c.execute('create table if not exists accounts(id text primary key,payload text,version integer not null)')
        if data is None:
            row=c.execute('select payload,version from accounts where id=?',(key,)).fetchone()
            return (json.loads(row[0]),row[1]) if row else (None,None)
        if version is None:c.execute('insert into accounts values(?,?,0)',(key,json.dumps(data)))
        else:
            q=c.execute('update accounts set payload=?,version=version+1 where id=? and version=?',(json.dumps(data),key,version))
            if q.rowcount!=1:raise ValueError('다른 화면에서 변경됐어요. 새로고침 후 다시 해 주세요.')
def save(d,v):db(st.session_state.uid,d,v);st.rerun()

def hashed(s):return hashlib.sha256(s.encode()).hexdigest()
def day_entries(d,key):return [x for x in d.get(key,[]) if x['date']==str(TODAY)]
def burn(met,kg,minutes):return round(met*3.5*kg/200*minutes)
FOODS={'밥 1공기 (약 210g)':310,'삶은 달걀 1개':75,'바나나 1개':100,'우유 200ml':125,'두부 150g':120,'닭가슴살 100g':165,'사과 1개':95,'고구마 100g':130,'김밥 1줄':450,'라면 1봉':500}
MOVES={'가벼운 걷기':2.5,'보통 걷기':3.5,'실내 자전거 (가볍게)':3.5,'가벼운 스트레칭':2.3}
@st.cache_data(ttl=600,show_spinner=False)
def places(key,area,word,radius):
    h={'Authorization':'KakaoAK '+key}
    r=requests.get('https://dapi.kakao.com/v2/local/search/keyword.json',headers=h,params={'query':area,'size':1},timeout=15);r.raise_for_status()
    anchors=r.json()['documents']
    if not anchors:return [],None
    center=anchors[0]
    r=requests.get('https://dapi.kakao.com/v2/local/search/keyword.json',headers=h,params={'query':word,'x':center['x'],'y':center['y'],'radius':radius,'sort':'distance','size':10},timeout=15);r.raise_for_status()
    return r.json()['documents'],center
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
:root{color-scheme:light}html,body,.stApp,[data-testid="stAppViewContainer"]{background:#F3F8EF!important;color:#254B37!important}.block-container{max-width:780px;padding-top:3.7rem;padding-bottom:2rem}
h1,h2,h3{font-family:'Jua',sans-serif!important;color:#315E42!important}p,label,summary,li{color:#254B37!important}
input,textarea,[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"]>div{background:#FFF!important;color:#254B37!important;-webkit-text-fill-color:#254B37!important}
[data-testid="stAlert"]{background:#E4F1DE!important;color:#254B37!important}[data-testid="stAlert"] *{color:#254B37!important}
.stButton>button,.stFormSubmitButton>button{border-radius:15px;min-height:46px;background:#E5F0DD;color:#254B37;border:1px solid #B5CEAB}.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:#39875C;color:white}.stButton>button[kind="primary"] p,.stFormSubmitButton>button[kind="primary"] p{color:white!important}
[data-testid="stSidebar"]{background:#E5F0DD!important;left:auto!important;right:0!important;border-left:1px solid #BED3AE}[data-testid="stSidebar"][aria-expanded="true"]{transform:none!important}[data-testid="stSidebar"][aria-expanded="false"]{transform:translateX(100%)!important}[data-testid="stSidebarCollapsedControl"]{left:auto!important;right:.5rem!important}
.hero{padding:18px;border:1px solid #BED3AE;border-radius:22px;background:#E6F1DD;margin-bottom:16px}.hero h1{margin:0;font-size:32px}.hero p{margin:5px 0 0}
[data-testid="stMetric"]{padding:12px;background:white;border:1px solid #D8E6D0;border-radius:16px}
[data-testid="stSidebar"] [role="radiogroup"]{gap:14px!important}
[data-testid="stSidebar"] [role="radiogroup"] label{background:#FFF!important;padding:16px!important;border:1px solid #B7CFA9;border-radius:15px;width:100%;min-height:58px}
[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:19px!important;font-weight:700}
[data-testid="stSidebarCollapsedControl"] button{min-width:56px!important;min-height:56px!important;background:#C8E2B9!important;border:2px solid #39875C!important;border-radius:14px!important}
</style>''',unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🌱 초록하루</h1><p>식사 기록 · 맞춤 운동 · 가까운 운동 장소</p></div>',unsafe_allow_html=True)
try:
    if 'uid' not in st.session_state:
        a,b=st.tabs(['처음 시작','내 기록 불러오기'])
        with a:
            with st.form('join'):
                name=st.text_input('별명',max_chars=20)
                age=st.number_input('나이',min_value=1,max_value=110,value=35)
                if st.form_submit_button('나만의 플래너 만들기',type='primary',use_container_width=True):
                    if not name.strip():st.error('별명을 입력해 주세요.')
                    else:
                        code=secrets.token_hex(12).upper();uid=hashed(code)
                        db(uid,{'name':name.strip(),'age':int(age),'foods':[],'moves':[],'checks':{},'created':str(TODAY)})
                        st.session_state.uid=uid;st.session_state.new_code=code;st.rerun()
        with b:
            with st.form('restore'):
                code=st.text_input('개인 코드',type='password')
                if st.form_submit_button('불러오기'):
                    uid=hashed(code.strip().upper());found,_=db(uid)
                    if found:st.session_state.uid=uid;st.rerun()
                    else:st.error('코드를 확인해 주세요.')
        st.caption('체중 감량 처방이 아닌 생활습관 플래너입니다. 개인 코드는 비밀번호처럼 보관하세요.')
        st.stop()
    d,v=db(st.session_state.uid)
    if not d:st.error('저장된 계정을 찾지 못했어요.');st.stop()
    if 'new_code' in st.session_state:
        st.success('개인 코드: '+st.session_state.new_code)
        st.caption('다른 기기에서 이 코드로 접속해요. 화면을 닫기 전에 따로 보관하세요.')
        if st.button('코드 보관했어요'):del st.session_state.new_code;st.rerun()
    st.sidebar.markdown('## 🌿 나의 도구함')
    menu=st.sidebar.radio('메뉴',['오늘 식단·운동','주변 장소','주간 기록'],label_visibility='collapsed')
    st.sidebar.caption(d['name']+'님의 건강 습관')
    with st.sidebar.expander('내 정보 수정'):
        if st.button('성별 · 나이 · 몸무게 수정'):d['profile_ready']=False;save(d,v)
        st.download_button('기록 백업',json.dumps(d,ensure_ascii=False),'green_day.json',mime='application/json')
        if st.button('로그아웃'):st.session_state.clear();st.rerun()
    if not remote():st.sidebar.caption('체험 저장 · 서버 초기화 시 유실 가능')
    if not d.get('profile_ready'):
        st.subheader('나에게 맞게, 1분 설정 🌿')
        with st.form('quick_profile'):
            c1,c2=st.columns(2)
            age=c1.number_input('나이',1,110,int(d['age']))
            sex=c2.selectbox('성별',['선택 안 함','여자','남자'],index=['선택 안 함','여자','남자'].index({'여성':'여자','남성':'남자'}.get(d.get('sex'),d.get('sex','선택 안 함'))))
            c1,c2=st.columns(2)
            kg=c1.number_input('현재 몸무게 kg',20.0,250.0,float(d.get('kg',65.0)),.1)
            goal=c2.number_input('희망 몸무게 kg (성인 참고용)',20.0,250.0,float(d.get('goal',kg)),.1)
            allergy=st.text_input('알레르기·못 먹는 음식 (없으면 비워두기)',value=d.get('allergy',''))
            st.caption('성장기는 희망 체중을 저장하지 않아요. 성인도 이 값만으로 감량 처방이나 달성일을 계산하지 않아요.')
            if st.form_submit_button('설정 완료',type='primary',use_container_width=True):
                d.update(age=int(age),sex=sex,kg=kg,profile_ready=True)
                d['allergy']=allergy.strip()
                if age>=19:d['goal']=goal
                else:d.pop('goal',None)
                save(d,v)
        st.stop()
    adult=d['age']>=19
    foods=day_entries(d,'foods');moves=day_entries(d,'moves')
    if menu=='오늘 식단·운동':
        st.subheader('오늘 먹을 식단을 적어주세요 🍱')
        with st.expander('🌷 오늘 미션 · 나의 정원',expanded=True):
            garden=d.get('garden',{})
            entry=garden.get(str(TODAY),{})
            earned=sum(sum(bool(row.get(k,False)) for k in ['meal','move','rest']) for row in garden.values())
            spent=sum(int(x.get('cost',0)) for x in d.get('garden_items',[]))
            balance=max(0,earned-spent)
            stage=['🌱 새싹','🌿 잎사귀','🌷 꽃봉오리','🌸 꽃밭'][min(3,earned//6)]
            st.markdown(f'### {stage}　·　💧 {balance}개')
            st.caption('하루 최대 3개 · 미완료 벌점 없음 · 지난 실천은 사라지지 않아요.')
            with st.form('garden_missions'):
                meal=st.checkbox('🍱 실제 먹은 식사 기록했어요',value=entry.get('meal',False))
                meal_note=st.text_input('먹은 식사 한 줄',value=entry.get('meal_note',''),placeholder='예: 점심에 비빔밥과 달걀')
                move=st.checkbox('👟 편안하게 움직였어요 / 필요한 휴식을 취했어요',value=entry.get('move',False))
                rest=st.checkbox('🌙 오늘 컨디션을 돌아봤어요',value=entry.get('rest',False))
                mood=st.select_slider('오늘 컨디션',options=['쉬고 싶어요','보통이에요','좋아요'],value=entry.get('mood','보통이에요'))
                if st.form_submit_button('미션 저장 · 물방울 받기',use_container_width=True):
                    if meal and not meal_note.strip():st.warning('실제로 먹은 식사를 한 줄 남겨주세요.')
                    else:
                        d.setdefault('garden',{})[str(TODAY)]={'meal':meal,'meal_note':meal_note.strip(),'move':move,'rest':rest,'mood':mood}
                        save(d,v)
            if all(entry.get(k,False) for k in ['meal','move','rest']):st.success('오늘의 세 가지 실천 완료! 🌼')
            with st.expander('🎨 정원 꾸미기'):
                owned=[x['name'] for x in d.get('garden_items',[])]
                item=st.selectbox('아이템 (각 💧 3개)',['🪴 작은 화분','🐸 개구리 친구','🦋 나비 장식','🌻 해바라기'])
                if st.button('물방울로 데려오기',use_container_width=True):
                    if item in owned:st.info('이미 가지고 있어요.')
                    elif balance<3:st.info('물방울을 3개 모으면 데려올 수 있어요.')
                    else:
                        d.setdefault('garden_items',[]).append({'name':item,'cost':3})
                        save(d,v)
                if owned:st.write(' '.join(owned))
            with st.expander('🍰 즐기는 식사 달력'):
                st.caption('미션과 관계없이 좋아하는 음식을 즐길 수 있어요. 다음 날 굶거나 운동으로 벌충할 필요 없어요.')
                with st.form('enjoy_meal'):
                    enjoy_date=st.date_input('날짜',value=TODAY)
                    enjoy_note=st.text_input('즐기고 싶은 식사',placeholder='예: 가족과 피자 먹기',max_chars=100)
                    if st.form_submit_button('일정 저장',use_container_width=True):
                        if enjoy_note.strip():
                            d.setdefault('enjoy_meals',{})[str(enjoy_date)]=enjoy_note.strip();save(d,v)
                for day,note in sorted(d.get('enjoy_meals',{}).items()):
                    a,b=st.columns([5,1]);a.write(day+' · '+note)
                    if b.button('삭제',key='enjoy_'+day):del d['enjoy_meals'][day];save(d,v)

        st.caption('자유 입력을 식품군 단어로 살펴보는 간단한 점검이에요. 영양 분석이나 알레르기 검사는 아니에요.')
        if adult:st.caption(f"현재 {d['kg']:g} kg → 희망 {d.get('goal',d['kg']):g} kg · 희망값은 적정 체중 판단이 아니에요.")
        else:st.caption('성장기 모드 · 규칙적인 식사와 즐거운 활동 중심')
        with st.form('daily_plan'):
            text=st.text_area('식단',value=d.get('menu_text',''),placeholder='아침: 밥, 달걀 / 점심: 비빔밥 / 저녁: 생선, 밥, 나물',height=95,label_visibility='collapsed')
            c1,c2=st.columns(2)
            minutes=c1.select_slider('운동할 시간 (분)',options=[5,10,15,20,30,40],value=20,format_func=lambda n:f'{n}분')
            where=c2.selectbox('운동 장소',['야외','집'])
            pain=st.checkbox('통증·어지럼이 있거나 운동 제한을 안내받았어요')
            submit=st.form_submit_button('식단 피드백 + 오늘 운동 보기',type='primary',use_container_width=True)
            if submit:
                if not text.strip():st.warning('먹을 음식을 적어주세요.')
                else:
                    d.update(menu_text=text,review={'date':str(TODAY),'text':text,'minutes':minutes,'where':where,'pain':pain})
                    save(d,v)
        with st.container(border=True):
            st.markdown('### 🍽️ 다음 식사 추천')
            st.write('**밥 + 단백질 반찬 + 채소 + 과일**을 기본으로 골라보세요.')
            st.caption('단백질: 생선·달걀·두부 / 식이섬유: 채소·콩·통곡물·과일 / 지방: 견과류·식물성 기름 등. 물도 곁들이세요.')
            options=[
                ('현미밥 + 두부구이 + 나물 + 사과','두부 · 콩 · 대두'),
                ('밥 + 달걀찜 + 데친 브로콜리 + 귤','달걀 · 계란'),
                ('밥 + 구운 생선 + 채소 반찬 + 배','생선 · 고등어'),
                ('통밀빵 + 닭고기 + 샐러드 + 바나나','밀 · 닭 · 글루텐'),
            ]
            avoid=d.get('allergy','').replace('，',',').replace('·',',')
            tokens=[z.strip() for z in avoid.split(',') if z.strip()]
            safe=[x for x in options if not any(z in x[0]+' '+x[1] for z in tokens)]
            if tokens:st.warning('피하는 음식: '+avoid+' · 단순 단어 제외만 적용해요. 숨은 재료·교차접촉을 걸러내지 못하므로 제품과 조리 재료를 직접 확인하세요.')
            if safe:
                index=st.session_state.get('meal_index',0)%len(safe)
                st.success(safe[index][0])
                if st.button('다른 식단 보기',use_container_width=True):st.session_state.meal_index=index+1;st.rerun()
            else:st.info('기본 추천에서 제외할 재료가 많아요. 안전한 식단은 전문가와 확인해 주세요.')
            st.caption('일반적인 식품군 조합 예시이며 개인별 영양 처방이 아니에요. 분량·질환·약물에 따라 적절성이 달라집니다.')
        review=d.get('review')
        if review and review['date']==str(TODAY):
            txt=review['text']
            protein=any(w in txt for w in ['고기','생선','두부','달걀','계란','콩','닭','우유','요거트'])
            veg=any(w in txt for w in ['채소','나물','샐러드','당근','브로콜리','오이','양배추','비빔밥'])
            fiber=any(w in txt for w in ['채소','나물','샐러드','현미','통밀','콩','과일','사과','배','귤','브로콜리','오이','양배추'])
            carbs=any(w in txt for w in ['밥','빵','감자','고구마','면','오트','죽'])
            missing=[name for ok,name in [(protein,'단백질 식품'),(veg,'채소'),(carbs,'곡류·전분 식품'),(fiber,'식이섬유 식품')] if not ok]
            with st.container(border=True):
                st.markdown('### 🥗 식단 한눈에')
                st.write('**보완 제안:** '+('기록에서 '+', '.join(missing)+' 표현을 찾지 못했어요. 실제 식단에 없다면 한 가지 곁들여 보세요.' if missing else '곡류·단백질·채소 표현이 보여요. 실제 분량과 조리법도 함께 확인해 주세요.'))
                st.caption('음식 이름만 확인한 참고 결과예요. 음식이 빠졌다고 단정하거나 식단이 충분하다고 평가하지 않아요.')
            with st.container(border=True):
                st.markdown('### 👟 오늘의 운동')
                if review['pain']:st.write('오늘은 자동 운동 추천을 쉬어요. 증상과 안전한 운동 범위를 의료진에게 확인하세요.')
                else:
                    activity='편안한 걷기' if review['where']=='야외' else '가벼운 스트레칭과 제자리 걷기'
                    st.write(f"**{activity} · {review['minutes']}분**")
                    st.caption('숨이 편안한 강도로 시작하고 통증이 생기면 중단하세요. 먹은 음식을 벌충하기 위한 운동이 아니에요.')
                    if st.button('오늘 운동 완료 ✓',use_container_width=True):
                        if not any(x.get('daily') and x['date']==str(TODAY) for x in d['moves']):d['moves'].append({'date':str(TODAY),'name':activity,'minutes':review['minutes'],'daily':True})
                        save(d,v)
                    if any(x.get('daily') and x['date']==str(TODAY) for x in d['moves']):st.success('오늘 활동을 기록했어요 🌱')
    elif menu=='주변 장소':
        st.subheader('📍 가까운 운동 장소 찾기')
        st.caption('집 주소 대신 동네·역 이름을 입력하세요. 검색 중심점 기준 직선거리이며 도보거리가 아닙니다.')
        with st.form('map'):
            area=st.text_input('동네 또는 역 이름',placeholder='예: 서울숲역')
            word=st.selectbox('장소 종류',['공원','산책로','운동장','체육센터'])
            radius=st.select_slider('반경',options=[500,1000,2000,5000],value=1000,format_func=lambda x:f'{x}m')
            search=st.form_submit_button('주변 찾기',type='primary',use_container_width=True)
        if search:
            if not area.strip():st.warning('동네를 입력해 주세요.')
            else:
                try:key=st.secrets.get('KAKAO_REST_API_KEY','')
                except Exception:key=''
                if not key:
                    st.info('지도 API 키가 없어 외부 지도 검색으로 연결해요. 반경 필터는 적용되지 않아요.')
                    st.link_button('지도에서 찾기','https://map.kakao.com/?q='+quote(area+' '+word),use_container_width=True)
                else:
                    rows,center=places(key,area,word,radius)
                    if center:st.caption('검색 중심: '+center['place_name'])
                    if not rows:st.info('검색 결과가 없어요. 지역이나 반경을 바꿔보세요.')
                    else:
                        st.map([{'lat':float(z['y']),'lon':float(z['x'])} for z in rows])
                        for x in rows:
                            st.markdown('**'+html.escape(x['place_name'])+'**');st.caption(x['address_name']+' · 직선거리 '+x.get('distance','?')+'m')
                            st.link_button('지도·길 찾기',x['place_url'])
                        st.caption('운영시간·이용요금·출입 가능 여부는 방문 전에 확인하세요.')
    else:
        st.subheader('📅 최근 7일, 나의 생활 리듬')
        days=[TODAY-timedelta(days=i) for i in range(6,-1,-1)]
        exercise=[sum(x['minutes'] for x in d['moves'] if x['date']==str(day)) for day in days]
        st.bar_chart({'날짜':[day.strftime('%m/%d') for day in days],'활동 시간(분)':exercise},x='날짜',y='활동 시간(분)',color='#39875C')
        dates=set(map(str,days));a,b=st.columns(2);a.metric('총 활동 시간',str(sum(exercise))+'분');b.metric('식사 기록한 날',str(len({x['date'] for x in d['foods'] if x['date'] in dates}))+'일')
        for day in reversed(days):
            with st.expander(day.strftime('%m월 %d일')):
                items=[x['name'] for x in d['foods'] if x['date']==str(day)]
                st.write('식사: '+(', '.join(items) if items else '기록 없음'))
                st.write('활동: '+str(exercise[days.index(day)])+'분')
        st.caption('기록이 없는 날은 실제로 먹거나 움직이지 않았다는 뜻이 아닙니다. 이 앱은 진단·치료·체중 감량을 보장하지 않아요.')
except (requests.RequestException,ValueError,sqlite3.Error,KeyError) as exc:
    st.error('연결 또는 저장에 실패했어요. 설정을 확인하고 다시 시도해 주세요. 입력은 저장되지 않았을 수 있어요.')
    with st.expander('오류 종류'):st.write(type(exc).__name__)
