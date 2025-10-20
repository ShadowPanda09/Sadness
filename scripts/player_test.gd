extends CharacterBody2D


const SPEED = 300.0
const JUMP_VELOCITY = -400.0
const ACCEL := 100.0

var input: Vector2


func _physics_process(delta: float) -> void:
	velocity = lerp(velocity, _get_input() * SPEED, delta * ACCEL)
	
	move_and_slide()

func _get_input():
	input.x = Input.get_action_strength("move_r") - Input.get_action_strength("move_l")
	input.y = Input.get_action_strength("move_d") - Input.get_action_strength("move_u")

	return input.normalized()
