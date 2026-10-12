# Typed network pattern

One feature module is the canonical owner for its command IDs: it creates send packets, subscribes typed receive handlers, applies state, and emits semantic signals. A server push uses the same typed receive class and handler path as a response. Parse only after the `is_ok()` error-first branch when the protocol does not guarantee an error body.

```gdscript
class_name SampleEventSendLoadInfo
extends SendPacket

const CMD_ID: int = 7101

func _init() -> void:
	cmd_id = CMD_ID


func build() -> PackedByteArray:
	var buffer := PacketBuffer.new()
	buffer.put_int(0) # request version
	return buffer.get_data()
```

```gdscript
class_name SampleEventRecvLoadInfo
extends RecvPacket

const CMD_ID: int = SampleEventSendLoadInfo.CMD_ID

var info: SampleEventInfo = SampleEventInfo.new()

func _init() -> void:
	cmd_id = CMD_ID


func parse(cmd: int, error_code: int, buffer: PacketBuffer) -> void:
	super(cmd, error_code, buffer)
	if not is_ok():
		return
	info.event_id = buffer.get_int("event_id")
	info.remaining_seconds = buffer.get_int("remaining_seconds")
```

```gdscript
# In SampleEventModule.on_init()
NetworkService.subscribe(SampleEventSendLoadInfo.CMD_ID, SampleEventRecvLoadInfo, _on_recv_load_info)

func request_load_info() -> void:
	NetworkService.send_packet(SampleEventSendLoadInfo.new())

func _on_recv_load_info(packet: SampleEventRecvLoadInfo) -> void:
	if not packet.is_ok():
		load_failed.emit(packet.error_code)
		return
	_util.set_info(packet.info) # response and server push follow this same path
	info_changed.emit(packet.info)
```

## Contract tests

```gdscript
extends GutTest

const SpyNetClient := preload("res://tests/system/helpers/spy_net_client.gd")

var _old_connection: NetClient
var _spy: NetClient


func before_each() -> void:
	_old_connection = NetworkService._connection
	_spy = SpyNetClient.new()
	NetworkService._connection = _spy


func after_each() -> void:
	NetworkService._connection = _old_connection
	_spy = null
	_old_connection = null


func test_load_info_packet_round_trips_payload() -> void:
	var send := SampleEventSendLoadInfo.new()
	var decoded := PacketBuffer.from_bytes(send.build())
	assert_eq(decoded.get_int("request_version"), 0)


func test_recv_load_info_parses_success_payload() -> void:
	var writer := PacketBuffer.new()
	writer.put_int(42)
	writer.put_int(90)
	var packet := SampleEventRecvLoadInfo.new()
	packet.parse(packet.CMD_ID, ErrorCode.SUCCESS, PacketBuffer.from_bytes(writer.get_data()))
	assert_true(packet.is_ok())
	assert_eq(packet.info.event_id, 42)
	assert_eq(packet.info.remaining_seconds, 90)


func test_request_load_info_sends_expected_command() -> void:
	var module := SampleEventModule.new()
	module.request_load_info()
	assert_eq(_spy.get("sent_cmds"), [SampleEventSendLoadInfo.CMD_ID])
```

**Legacy rejection:** UI must not subscribe to packets or parse packet classes, and `ModuleMgr.broadcast` is not a feature routing mechanism. The canonical module remains the sole owner; do not duplicate subscriptions in util, model, screen, or popup code.
