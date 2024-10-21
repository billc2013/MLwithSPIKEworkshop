# Smart Walker Q-learning Code

#####
#TO DO:
# 1) think through how to communicate to the user robot motor direction and what to change.  For instance in my robot, at first it was going backward so I reversed the '-' signs in the drive function
# 2) communicate to the user how many episodes to train
# 3) check to see if you can train more episodes after you start testing... is the training data "saved"?
# 4) display in the console how many steps are being executed per episode??
# 5) communicate to user the +/- margin for pointing it in a constant direction... how perfect do they need to reset it each time?
# 6) add into the experience --> run both motors at the same velocity to see what the robot does with no training...
# 7) what if the challenge is to try to drive straight out of a door.  Explore with no training and see that you can't make it out the door... Ideally do this with just simple motor commands (velocity = 50,50 for the two motors) AND then do this with no training in the RL code.
# 7 continued .... then train for X # of episodes and try again... add training episodes until you make it out the door.  Observe how the robot is utilizing it's training to "correct" for getting off kilter.
# 8) UPDATE --> I added a print statement so you can track the rewards for each state action pair.
# 9) UPDATE --> I made one leg shorter so that without training, the bot always goes left.  With training...

import motor
from hub import port, motion_sensor, button, light_matrix, sound
import random
import runloop

# Define Volume of the speaker for UI
sound.volume(50)

# Constants
motorR_port = port.A
motorL_port = port.B
motor_slow = 50
motor_medium = 70
motor_fast = 90
motor_stop = 0
yaw_threshold = 1400
num_steps_per_episode = 30
test_extra = 2# Testing step multiplier
StateSpace = [-3, -2, -1, 0, 1, 2, 3]
RewardSpace = [-25, -10, -2, 10, -2, -10, -25]
ActionSpace = [
	[motor_slow, motor_slow], [motor_slow, motor_medium], [motor_slow, motor_fast],
	[motor_medium, motor_slow], [motor_medium, motor_medium], [motor_medium, motor_fast],
	[motor_fast, motor_slow], [motor_fast, motor_medium], [motor_fast, motor_fast],
	[motor_stop, motor_slow], [motor_slow, motor_stop],
	[motor_stop, motor_medium], [motor_medium, motor_stop],
	[motor_stop, motor_fast], [motor_fast, motor_stop]
]

# Learning parameters
gamma = 0.9
alpha = 0.1

# Initialize the Q-table with all zeros
def initialize_q_table(num_states, num_actions):
	return [[0] * num_actions for _ in range(num_states)]

# Get state based on orientation
def get_hub_state():
	current_angle = motion_sensor.tilt_angles()[0]
	if current_angle < -400:
		return -3
	elif current_angle < -200:
		return -2
	elif current_angle < -50:
		return -1
	elif current_angle > 400:
		return 3
	elif current_angle > 200:
		return 2
	elif current_angle > 50:
		return 1
	else:
		return 0

# Greedy action selection
def select_action(state, q_table, epsilon=0.0):
	k = random.random()
	if epsilon > k:
		return ActionSpace[random.randint(0, len(ActionSpace) - 1)]
	else:
		state_index = StateSpace.index(state)
		action_array = q_table[state_index]
		action_index = action_array.index(max(action_array))
		return ActionSpace[action_index]

# Q-value update
def update_q(q_table, state, action, reward, next_state):
	qvalue = q_table[StateSpace.index(state)][ActionSpace.index(action)]
	new_q = (1 - alpha) * qvalue + alpha * (reward + gamma * max(q_table[StateSpace.index(next_state)]))
	q_table[StateSpace.index(state)][ActionSpace.index(action)] = new_q

# Drive motors
def drive(action):
	right_velocity = action[0]
	left_velocity = action[1]
	motor.run(motorR_port, -right_velocity) # Right motor forward
	motor.run(motorL_port, left_velocity)# Left motor forward

# Training function
async def train(q_table):
	step = 0
	epsilon = 0.9
	while step < num_steps_per_episode:
		state = get_hub_state()
		action = select_action(state, q_table, epsilon)
		drive(action)
		await runloop.sleep_ms(500)

		new_state = get_hub_state()
		reward = RewardSpace[StateSpace.index(new_state)]
		update_q(q_table, state, action, reward, new_state)

		# Print reward
		print("Train - Step: {}, From state: {}, To state: {}, Reward: {}".format(step, state, new_state, reward))

		step += 1
		epsilon = max(0.4, epsilon - 0.008)# Epsilon decay

		current_direction = motion_sensor.tilt_angles()[0]
		if abs(current_direction) > yaw_threshold:
			print('Training: Robot turned too much, halting episode!')
			break

	motor.stop(motorR_port, stop=motor.COAST)
	motor.stop(motorL_port, stop=motor.COAST)

# Testing function
async def test(q_table):
	step = 0
	while step < num_steps_per_episode * test_extra:
		state = get_hub_state()
		action = select_action(state, q_table, epsilon=0)# Epsilon=0 for full exploitation
		drive(action)
		await runloop.sleep_ms(500)

		new_state = get_hub_state()
		reward = RewardSpace[StateSpace.index(new_state)]

		# Print reward
		print("Test - Step: {}, From state: {}, To state: {}, Reward: {}".format(step, state, new_state, reward))

		step += 1

		current_direction = motion_sensor.tilt_angles()[0]
		if abs(current_direction) > yaw_threshold:
			print('Testing: Robot turned too much, halting sequence!')
			break

	motor.stop(motorR_port, stop=motor.COAST)
	motor.stop(motorL_port, stop=motor.COAST)

# Main logic
async def main():
	qtable = initialize_q_table(len(StateSpace), len(ActionSpace))
	episode = 0

	while True:
		light_matrix.write(str(episode))

		if button.pressed(button.RIGHT):
			sound.beep(1000, 1000, 100)
			await train(qtable)
			episode += 1
		elif button.pressed(button.LEFT):
			sound.beep(1000, 1000, 100)
			light_matrix.write('Test')
			await test(qtable)
		else:
			await runloop.sleep_ms(200)

runloop.run(main())

