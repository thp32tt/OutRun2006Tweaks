# A Review Ledger — A-20260923T0600KST
- target: `539fecf218d39cea103da6ccc23f59eb7498185f`
- fresh_units: 75
- carried_forward_units: 75
- review_units_completed: 150
- protected runtime baseline: R51 `17ad376bfdf7939f0851c0c629e4fa094a84f28a`

## Fresh evidence rows
001 FRESH cross main.cpp::FindGameProcess shared PID→active process; blob 6ac44a156e93458ecbf0b9b06028ff89b97f0088 PASS.
002 FRESH adversarial main.cpp::FindGameProcess stale PID/restart PASS.
003 FRESH lifetime main.cpp::FindGameProcess identity reselect PASS.
004 FRESH cross main.cpp::SharedClientPid header→PID trust PASS.
005 FRESH adversarial main.cpp::SharedClientPid malformed header rejected PASS.
006 FRESH lifetime main.cpp::SharedClientPid map/view/handle release PASS.
007 FRESH cross main.cpp::ProcessAliveForSelection liveness→selection PASS.
008 FRESH adversarial main.cpp::ProcessAliveForSelection OpenProcess failure not alive PASS.
009 FRESH lifetime main.cpp::ProcessAliveForSelection handle close PASS.
010 FRESH cross main.cpp::ProcessCreationKey creation→newest PASS.
011 FRESH adversarial main.cpp::ProcessCreationKey PID reuse/tie PASS.
012 FRESH lifetime main.cpp::ProcessCreationKey handle lifetime PASS.
013 FRESH cross main.cpp::WaitForGameWindow startup→window readiness PASS.
014 FRESH adversarial main.cpp::WaitForGameWindow restart while polling PASS.
015 FRESH lifetime main.cpp::WaitForGameWindow no stale HWND retained PASS.
016 FRESH cross main.cpp::FindAdapter XR LUID→D3D adapter PASS.
017 FRESH adversarial main.cpp::FindAdapter no match throws PASS.
018 FRESH lifetime main.cpp::FindAdapter adapter/factory release PASS.
019 FRESH cross main.cpp::CreateD3D11Device feature-level→device PASS.
020 FRESH adversarial main.cpp::CreateD3D11Device failure releases adapter PASS.
021 FRESH lifetime main.cpp::CreateD3D11Device COM move ownership PASS.
022 FRESH cross main.cpp::D3DObjects::~D3DObjects context→device teardown PASS.
023 FRESH adversarial main.cpp::D3DObjects::operator= overwrite releases old PASS.
024 FRESH lifetime main.cpp::D3DObjects move nulling PASS.
025 FRESH cross main.cpp::QueryProcessLiveness liveness→ownership PASS.
026 FRESH adversarial main.cpp::QueryProcessLiveness access denied→Unknown PASS.
027 FRESH lifetime main.cpp::QueryProcessLiveness wait/close PASS.
028 FRESH cross main.cpp::SharedWriter ctor mapping→owner PASS.
029 FRESH adversarial main.cpp::SharedWriter ctor existing mapping race guarded PASS.
030 FRESH lifetime main.cpp::SharedWriter ctor partial construction cleanup reviewed PASS.
031 FRESH cross host_state_v3_writer.hpp::ctor mapping→ownership→publish; blob 65280826a6cebfe4279fec63da66effc57d4aca4 PASS.
032 FRESH adversarial HostStateV3Writer::ctor invalid existing header→throw+Reset(false) PASS.
033 FRESH lifetime HostStateV3Writer::ctor throwing constructor cleanup PASS.
034 FRESH cross HostStateV3Writer::AcquireOwnership liveness→CAS PASS.
035 FRESH adversarial AcquireOwnership Unknown owner refuses takeover PASS.
036 FRESH lifetime AcquireOwnership dead owner→self CAS bounded PASS.
037 FRESH cross HostStateV3Writer::Reset owner→dead publication→unmap PASS.
038 FRESH adversarial Reset foreign hostPid not zeroed PASS.
039 FRESH lifetime Reset view→handle→owns teardown PASS.
040 FRESH cross HostStateV3Writer::Publish state→seqlock wire PASS.
041 FRESH adversarial Publish !state/!owns returns 0 PASS.
042 FRESH lifetime Publish odd→memcpy→barrier→even PASS.
043 FRESH cross ReferenceSpaceChanged recenter→generation PASS.
044 FRESH adversarial ReferenceSpaceChanged wrap skips zero PASS.
045 FRESH lifetime ReferenceSpaceChanged persists to Publish PASS.
046 FRESH cross SyncReferenceSpaceGeneration external→writer PASS.
047 FRESH adversarial SyncReferenceSpaceGeneration(0)→1 PASS.
048 FRESH lifetime ReferenceSpaceGeneration read-after-sync PASS.
049 FRESH cross main_r23.cpp::R23UsableGameplayBootstrapFrame flags→authority; blob 70d25b6f9a4566d538dd9295e8dbba2b40f7e69d PASS.
050 FRESH adversarial R23UsableGameplayBootstrapFrame in-flight/failure/zero-pose rejected PASS.
051 FRESH lifetime R23UsableGameplayBootstrapFrame slot/generation/handles/dims validated PASS.
052 FRESH cross R37FrameIdBefore producer→consumer ordering PASS.
053 FRESH adversarial R37FrameIdBefore equal/wrap behavior PASS.
054 FRESH lifetime R37FrameIdBefore no ownership mutation PASS.
055 FRESH cross R23ReleaseDirectHoldResources hold→COM teardown PASS.
056 FRESH adversarial R23ReleaseDirectHoldResources partial resources null-safe PASS.
057 FRESH lifetime R23ReleaseDirectHoldResources identity reset PASS.
058 FRESH cross R23InvalidateDirectHold authority→invalid PASS.
059 FRESH adversarial R23InvalidateDirectHold allocated resources cannot remain authoritative PASS.
060 FRESH lifetime R23InvalidateDirectHold restage required PASS.
061 FRESH cross R23StageDirectHold ring→held copy PASS.
062 FRESH adversarial R23StageDirectHold mismatched desc/sample/dims rejected PASS.
063 FRESH lifetime R23StageDirectHold format/size change→recreate PASS.
064 FRESH cross R23DirectHoldState::~R23DirectHoldState shutdown→release PASS.
065 FRESH adversarial R23DirectHoldState dtor partial resources PASS.
066 FRESH lifetime R23DirectHoldState dtor two-eye release PASS.
067 FRESH cross R23AsyncPixelProbe::~R23AsyncPixelProbe diagnostics→staging teardown PASS.
068 FRESH adversarial R23AsyncPixelProbe dtor pending-map shutdown PASS.
069 FRESH lifetime R23AsyncPixelProbe dtor three stages released PASS.
070 FRESH cross R23AsyncPixelProbe::EnsureStage format→reuse/recreate PASS.
071 FRESH adversarial EnsureStage CreateTexture2D failure leaves UNKNOWN PASS.
072 FRESH lifetime EnsureStage old stage released before recreation PASS.
073 FRESH cross R23AsyncPixelProbe::ConsumeSource GPU→CPU diagnostic PASS.
074 FRESH adversarial ConsumeSource WAS_STILL_DRAWING preserves pending PASS.
075 FRESH lifetime ConsumeSource map/unmap/pending ordering PASS.

## Identity-validated carry-forward evidence rows
076 CARRY CF001 main.cpp::FindGameProcess target 539fecf218d3 blob 6ac44a156e93458ecbf0b9b06028ff89b97f0088 unchanged; prior PASS retained.
077 CARRY CF002 main.cpp::FindGameProcess same identity; prior independent restart objective retained.
078 CARRY CF003 main.cpp::FindGameProcess same identity; prior lifetime objective retained.
079 CARRY CF004 main.cpp::SharedClientPid same identity; prior PASS retained.
080 CARRY CF005 main.cpp::SharedClientPid same identity; malformed-header objective retained.
081 CARRY CF006 main.cpp::SharedClientPid same identity; mapping lifetime objective retained.
082 CARRY CF007 main.cpp::ProcessAliveForSelection same identity; prior PASS retained.
083 CARRY CF008 main.cpp::ProcessAliveForSelection same identity; failure objective retained.
084 CARRY CF009 main.cpp::ProcessAliveForSelection same identity; handle lifetime retained.
085 CARRY CF010 main.cpp::ProcessCreationKey same identity; prior PASS retained.
086 CARRY CF011 main.cpp::ProcessCreationKey same identity; PID-reuse objective retained.
087 CARRY CF012 main.cpp::ProcessCreationKey same identity; lifetime retained.
088 CARRY CF013 main.cpp::WaitForGameWindow same identity; prior PASS retained.
089 CARRY CF014 main.cpp::WaitForGameWindow same identity; restart objective retained.
090 CARRY CF015 main.cpp::WaitForGameWindow same identity; HWND lifetime retained.
091 CARRY CF016 main.cpp::FindAdapter same identity; prior PASS retained.
092 CARRY CF017 main.cpp::FindAdapter same identity; no-match objective retained.
093 CARRY CF018 main.cpp::FindAdapter same identity; release objective retained.
094 CARRY CF019 main.cpp::CreateD3D11Device same identity; prior PASS retained.
095 CARRY CF020 main.cpp::CreateD3D11Device same identity; failure objective retained.
096 CARRY CF021 main.cpp::CreateD3D11Device same identity; COM ownership retained.
097 CARRY CF022 main.cpp::D3DObjects::~D3DObjects same identity; prior PASS retained.
098 CARRY CF023 main.cpp::D3DObjects::operator= same identity; overwrite objective retained.
099 CARRY CF024 main.cpp::D3DObjects same identity; move lifetime retained.
100 CARRY CF025 main.cpp::QueryProcessLiveness same identity; prior PASS retained.
101 CARRY CF026 main.cpp::QueryProcessLiveness same identity; Unknown objective retained.
102 CARRY CF027 main.cpp::QueryProcessLiveness same identity; handle lifetime retained.
103 CARRY CF028 main.cpp::SharedWriter ctor same identity; prior PASS retained.
104 CARRY CF029 main.cpp::SharedWriter ctor same identity; race objective retained.
105 CARRY CF030 main.cpp::SharedWriter ctor same identity; cleanup objective retained.
106 CARRY CF031 HostStateV3Writer::ctor target 539fecf218d3 blob 65280826a6cebfe4279fec63da66effc57d4aca4 unchanged; prior PASS retained.
107 CARRY CF032 HostStateV3Writer::ctor same identity; invalid-header objective retained.
108 CARRY CF033 HostStateV3Writer::ctor same identity; throw cleanup retained.
109 CARRY CF034 AcquireOwnership same identity; prior PASS retained.
110 CARRY CF035 AcquireOwnership same identity; Unknown-owner objective retained.
111 CARRY CF036 AcquireOwnership same identity; CAS lifetime retained.
112 CARRY CF037 Reset same identity; prior PASS retained.
113 CARRY CF038 Reset same identity; foreign-owner objective retained.
114 CARRY CF039 Reset same identity; teardown objective retained.
115 CARRY CF040 Publish same identity; prior PASS retained.
116 CARRY CF041 Publish same identity; no-owner objective retained.
117 CARRY CF042 Publish same identity; seqlock ordering retained.
118 CARRY CF043 ReferenceSpaceChanged same identity; prior PASS retained.
119 CARRY CF044 ReferenceSpaceChanged same identity; wrap objective retained.
120 CARRY CF045 ReferenceSpaceChanged same identity; publication lifetime retained.
121 CARRY CF046 SyncReferenceSpaceGeneration same identity; prior PASS retained.
122 CARRY CF047 SyncReferenceSpaceGeneration same identity; zero objective retained.
123 CARRY CF048 ReferenceSpaceGeneration same identity; read-after-sync retained.
124 CARRY CF049 R23UsableGameplayBootstrapFrame target 539fecf218d3 blob 70d25b6f9a4566d538dd9295e8dbba2b40f7e69d unchanged; prior PASS retained.
125 CARRY CF050 R23UsableGameplayBootstrapFrame same identity; rejection objective retained.
126 CARRY CF051 R23UsableGameplayBootstrapFrame same identity; direct identity retained.
127 CARRY CF052 R37FrameIdBefore same identity; prior PASS retained.
128 CARRY CF053 R37FrameIdBefore same identity; wrap objective retained.
129 CARRY CF054 R37FrameIdBefore same identity; lifetime retained.
130 CARRY CF055 R23ReleaseDirectHoldResources same identity; prior PASS retained.
131 CARRY CF056 R23ReleaseDirectHoldResources same identity; partial-resource objective retained.
132 CARRY CF057 R23ReleaseDirectHoldResources same identity; reset objective retained.
133 CARRY CF058 R23InvalidateDirectHold same identity; prior PASS retained.
134 CARRY CF059 R23InvalidateDirectHold same identity; stale-authority objective retained.
135 CARRY CF060 R23InvalidateDirectHold same identity; restage objective retained.
136 CARRY CF061 R23StageDirectHold same identity; prior PASS retained.
137 CARRY CF062 R23StageDirectHold same identity; mismatch objective retained.
138 CARRY CF063 R23StageDirectHold same identity; recreate lifetime retained.
139 CARRY CF064 R23DirectHoldState dtor same identity; prior PASS retained.
140 CARRY CF065 R23DirectHoldState dtor same identity; partial objective retained.
141 CARRY CF066 R23DirectHoldState dtor same identity; eye release retained.
142 CARRY CF067 R23AsyncPixelProbe dtor same identity; prior PASS retained.
143 CARRY CF068 R23AsyncPixelProbe dtor same identity; pending objective retained.
144 CARRY CF069 R23AsyncPixelProbe dtor same identity; stage lifetime retained.
145 CARRY CF070 EnsureStage same identity; prior PASS retained.
146 CARRY CF071 EnsureStage same identity; creation-failure objective retained.
147 CARRY CF072 EnsureStage same identity; recreation lifetime retained.
148 CARRY CF073 ConsumeSource same identity; prior PASS retained.
149 CARRY CF074 ConsumeSource same identity; defer objective retained.
150 CARRY CF075 ConsumeSource same identity; map lifetime retained.

## Gate
cross-subsystem=25; adversarial=25; distinct functions/paths=25; outside-latest-delta=75; existing-finding-revalidation=3. R51 USER_RUNTIME_VERIFIED baseline remains protected; static evidence does not advance it. No new promoted A finding. Existing VR-R51-WORLD-STEREO-PRESERVE-001 baseline-regression risk remains READY_FOR_C without duplicate key.