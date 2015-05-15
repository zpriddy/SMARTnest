#! /usr/bin/python
#################################################
#					SMARTnest					#
#################################################
# Zachary Priddy - 2015 						#
# me@zpriddy.com 								#
#												#
# Features: 									#
#	- Data logging with daily data saved to a 	#
#		pickle file								#
#	- Daily Graph generated using pygal 		#
#################################################
#################################################


#########
#IMPORTS
#########
import argparse
import nest
import utils
import pickle
from datetime import *
import dateutil.parser
import threading
import pygal


#########
#VARS
#########
programName="nest_data_logger.py"
programDescription="This program calls the nest API to record data every two minutes to render a daily graph"


debug = False
verbose = False
one_time_run = False
smartNestEnabled = False
away_temp = 0


##################################################
#FUNCTIONS
##################################################

###########
# GET ARGS
##########
def getArgs():
	parser = argparse.ArgumentParser(prog=programName, description=programDescription)
	parser.add_argument("-u","--username",help="Nest Account Username",required=True)
	parser.add_argument("-p","--password",help="Nest Account Password",required=True)
	#parser.add_argument("-f","--accountfile",help="Nest Account Ifno Saved In File",required=False) #To Add In Later
	parser.add_argument("-d","--debug",help="Debug Mode - One Time Run and Debug Info",required=False,action="store_true")
	parser.add_argument("-v","--verbose",help="Verbose mode - Print logs each run time.", required=False, action="store_true")
	parser.add_argument("-o","--one-time-run", help="One Time Run - Do not start threading loop", required=False, action="store_true")
	parser.add_argument("-s","--smartnest", help="Enable Smart Nest Features", required=False, action="store_true")


	return parser.parse_args()

	###############################################
	# OTHER NOTES
	#
	# For groups of args [in this case one of the two is required]:
	# group = parser.add_mutually_exclusive_group(required=True)
	# group.add_argument("-a1", "--arg1", help="ARG HELP")
	# group.add_argument("-a2", "--arg2", help="ARG HELP")
	#
	# To make a bool thats true:
	# parser.add_argument("-a","--arg",help="ARG HELP", action="store_true")
	#
	###############################################

##############
# END OF ARGS
##############


def readUserFromFile(user,filename):
	print "Read Account File"

def nestAuth(user):
	myNest = nest.Nest(user.username,user.password,cache_ttl=0)
	return myNest

def smartLoop(nest):
	global debug
	global verbose
	global one_time_run
	global smartNestEnabled

	# THREADING LOOP - EVERY 120 SECONDS
	if(not one_time_run):
		if(debug): print "Starting Threading Process.. "
		threading.Timer(120,smartLoop,args=[nest]).start()
	print "Running Data Loop..."

	##############################
	# DATA LOGGING AND COLLECTION
	##############################
	dayLog = []
	log_filename = 'logs/' + str(datetime.now().year) + '-' + str(datetime.now().month) + '-' + str(datetime.now().day) + '.log'
	try:
		dayLog = pickle.load(open(log_filename, 'rb'))
		dayLogIndex = len(dayLog)
	except:
		print "No Current Log File"
		dayLogIndex = 0


	log = {}
	data = nest.devices[0]
	structure = nest.structures[0]
	deviceData(data,log)
	sharedData(data, log)
	weatherData(data,log)
	structureData(structure,log)

	log['$timestamp'] = datetime.now().isoformat()

	calcTotals(log,dayLog)

	################
	# SMARTnest
	###############
	if(smartNestEnabled):
		smartNest(nest,log,dayLog)
	else:
		log['proactive_fan_run'] = False #Has it tried to run the fan to extend time between cycles?
		log['proactive_fan_run_time'] = 0 # Time that the fan has been running this cycle
		log['nest_target_temp'] = log['target_temperature'] #Set Programmed Target Temp
		log['temp_target_temp_status'] = False #Have I chnaged the target temp to extend the cycle runtime?




	#######################
	# SAVING DATA TO FILES
	#######################

	dayLog.append(log)

	try:
		pickle.dump(dayLog,open(log_filename,'wb'))
	except:
		print "Error Saving Log"


	# PRINT TO SCREEN IF IN DEBUG
	if(verbose):
		for x in range(0,len(dayLog)):
			print dayLog[x]

	# GENERATE GRAPH
	generateGraph(dayLog)




def deviceData(data,log):
	global away_temp
	deviceData = data._device
	log['leaf_temp'] = utils.c_to_f(deviceData['leaf_threshold_cool'])
	away_temp = utils.c_to_f(deviceData['away_temperature_high'])


def sharedData(data,log):
	sharedData = data._shared
	log['target_type'] = sharedData['target_temperature_type']
	log['fan_state'] = sharedData['hvac_fan_state']
	log['target_temperature'] = utils.c_to_f(sharedData['target_temperature'])
	log['current_temperature'] = utils.c_to_f(sharedData['current_temperature'])
	log['ac_state'] = sharedData['hvac_ac_state']

def weatherData(data,log):
	weatherData = data.weather._current
	log['outside_temperature'] = weatherData['temp_f']

def structureData(structure,log):
	structureData = structure._structure
	log['away'] = structureData['away']

def calcTotals(log, dayLog):
	global away_temp
	dayLogLen = len(dayLog)
	if(dayLogLen == 0):
		log['total_run_time'] = 0
		log['total_run_time_home'] = 0
		log['total_run_time_away'] = 0
		log['total_trans_time'] = 0
		log['trans_time'] = False
	else:
		index = dayLogLen - 1 #list(dayLog)[dayLogLen-1]

		then = dateutil.parser.parse(dayLog[index]['$timestamp'])
		now = dateutil.parser.parse(log['$timestamp'])
		diff = now - then
		diff = diff.total_seconds()/60

		if(log['ac_state'] == False and dayLog[index]['ac_state'] == False):
			log['total_run_time'] = dayLog[index]['total_run_time']
			log['total_run_time_home'] = dayLog[index]['total_run_time_home']
			log['total_run_time_away'] = dayLog[index]['total_run_time_away']
			log['trans_time'] = False
			log['total_trans_time'] = dayLog[index]['total_trans_time']
		elif(log['ac_state'] == True and dayLog[index]['ac_state'] == False):
			log['total_run_time'] = dayLog[index]['total_run_time']
			log['total_run_time_home'] = dayLog[index]['total_run_time_home']
			log['total_run_time_away'] = dayLog[index]['total_run_time_away']
			log['trans_time'] = False
			log['total_trans_time'] = dayLog[index]['total_trans_time']
		else:
			log['total_run_time'] = dayLog[index]['total_run_time'] + diff
			if(log['away']):
				print "CURRENTLY AWAY"
				log['total_run_time_away'] = dayLog[index]['total_run_time_away'] + diff
				log['total_run_time_home'] = dayLog[index]['total_run_time_home']
				log['target_temperature'] = away_temp
			elif(not log['away']):
				log['total_run_time_home'] = dayLog[index]['total_run_time_home'] + diff
				log['total_run_time_away'] = dayLog[index]['total_run_time_away']

		if(log['away'] == False and dayLog[index]['away'] == True and log['ac_state'] == True):
			log['trans_time'] = True
			log['total_trans_time'] = dayLog[index]['total_trans_time'] + diff
		elif(log['away'] == False and dayLog[index]['away'] == False and log['ac_state'] == True and dayLog[index]['trans_time'] == True):
			log['trans_time'] = True
			log['total_trans_time'] = dayLog[index]['total_trans_time'] + diff
		else:
			log['trans_time'] = False
			log['total_trans_time'] = dayLog[index]['total_trans_time']

	if(log['away']):
		log['target_temperature'] = away_temp




def generateGraph(dayLog):
	global smartNestEnabled

	timestamps = []
	total_run_time = []
	total_run_time_home = []
	total_run_time_away = []
	total_trans_time = []
	target_temperature = []
	smartNest_target_temp = []
	current_temperature = []
	outside_temperature = []

	for log in dayLog:
		timestamps.append(log['$timestamp'])
		total_run_time.append(log['total_run_time'])
		total_run_time_home.append(log['total_run_time_home'])
		total_run_time_away.append(log['total_run_time_away'])
		total_trans_time.append(log['total_trans_time'])
		target_temperature.append(log['nest_target_temp'])
		smartNest_target_temp.append(log['target_temperature'])
		current_temperature.append(log['current_temperature'])
		outside_temperature.append(log['outside_temperature'])

	line_chart = pygal.Line(x_label_rotation=20,x_labels_major_every=30,show_minor_x_labels=False,dots_size=.2,width=1200,tooltip_border_radius=2)
	line_chart.title = 'Daily Nest Usage'
	line_chart.x_labels = timestamps
	line_chart.add('Total Run Time', total_run_time)
	line_chart.add('Home Run Time', total_run_time_home)
	line_chart.add('Away Run Time', total_run_time_away)
	line_chart.add('Trans Run Time', total_trans_time)
	line_chart.add('Target Temperature', target_temperature)
	if(smartNestEnabled): line_chart.add('SMARTnest Adj Temperature', smartNest_target_temp)
	line_chart.add('Inside Temperature', current_temperature)
	line_chart.add('Outside Temperature', outside_temperature)

	line_chart.render_to_file('daily.svg')


def smartNest(nest, log, dayLog):
	global debug
	if(debug): print "SMARTnest Function..."
	controlData = {} #This is a place holder for data that I am going to send to the nest
	# FIRST TIME RUN?
	controlData['fan_state'] = None
	controlData['target_temperature'] = None

	dayLogLen = len(dayLog)
	if(dayLogLen == 0):
		if(debug): print "\t First Run.. Setting Defaults"
		log['proactive_fan_run'] = False #Has it tried to run the fan to extend time between cycles?
		controlData['fan_state'] = False
		#TEMP
		sendFanCommand(nest, "auto")
		log['proactive_fan_run_time'] = 0 # Time that the fan has been running this cycle
		log['nest_target_temp'] = log['target_temperature'] #Set Programmed Target Temp
		log['temp_target_temp_status'] = False #Have I chnaged the target temp to extend the cycle runtime?


	else: #This is where the fun starts!
		index = dayLogLen - 1
		if(log['ac_state'] == True and log['away'] == False): #If the AC is currently running and in home mode..
			if(debug): print "\tAC is on and in Home Mode.."
			log['proactive_fan_run'] = False # RESET FAN STATES
			log['proactive_fan_run_time'] = 0
			controlData['fan_state'] = False
			#TEMP
			sendFanCommand(nest, "auto")

			if(dayLog[index]['temp_target_temp_status'] == False): #IF the temp has not been chnaged
				#Lower the target temp by one degree
				if(debug): print "\t\tTemp has not been changed.."
				log['nest_target_temp'] = log['target_temperature']
				log['target_temperature'] = log['nest_target_temp'] - 1.0
				controlData['target_temperature'] = log['target_temperature']
				##Temp
				sendTempCommand(nest,log['target_temperature'])
				log['temp_target_temp_status'] = True

			elif(dayLog[index]['temp_target_temp_status'] == True and log['target_temperature'] == dayLog[index]['target_temperature']): #IF the temp has been chnaged and the temp was not changed atuomaticlly or manually..
				if(debug): print "\t\tTemp has been changed by SMARTnest but not by the nest or user"
				log['nest_target_temp'] = dayLog[index]['nest_target_temp']
				log['target_temperature'] = dayLog[index]['target_temperature']
				log['temp_target_temp_status'] = True

			else:
				if(debug): print "\t\tTemp has been changed by the nest or user.. Resetting.."
				log['nest_target_temp'] = log['target_temperature']
				log['target_temperature'] = log['nest_target_temp']
				log['temp_target_temp_status'] = False

		elif(log['ac_state'] == True and log['away'] == True):
			if(debug): print "\tAC is on and in Away Mode.. Resetting Fan States"
			log['proactive_fan_run'] = False # RESET FAN STATES
			log['proactive_fan_run_time'] = 0


		elif(log['ac_state'] == False): #IF the AC is not currently running..
			if(debug): print "\tAC is off.."
			if(dayLog[index]['temp_target_temp_status'] == False): #IF the temp has already been chnaged back
				if(debug): print "\t\tTemp has already been reset.."
				log['nest_target_temp'] = log['target_temperature']
				log['target_temperature'] = log['nest_target_temp']
				log['temp_target_temp_status'] = False
				log['proactive_fan_run'] = dayLog[index]['proactive_fan_run']

			elif(dayLog[index]['temp_target_temp_status'] == True and log['target_temperature'] == dayLog[index]['target_temperature']): #IF the temp has not been chnaged back and the temp was not changed atuomaticlly or manually..
				if(debug): print "\t\tTemp has not been reset and has not been changed by the user or the nest.. Resetting.."
				log['nest_target_temp'] = dayLog[index]['nest_target_temp']
				log['target_temperature'] = dayLog[index]['nest_target_temp'] #Reset target temp to what was stored in the temp value
				controlData['target_temperature'] = log['target_temperature']
				## Temp
				sendTempCommand(nest,log['target_temperature'])
				log['temp_target_temp_status'] = False
				log['proactive_fan_run'] = False # RESET FAN STATES

			else:
				if(debug): print "\t\tTemp has been changed by the user or the nest.. Resetting states to current.."
				log['nest_target_temp'] = log['target_temperature']
				log['target_temperature'] = log['nest_target_temp']
				log['temp_target_temp_status'] = False
				log['proactive_fan_run'] = False # RESET FAN STATES

			if(dayLog[index]['proactive_fan_run'] == False): #If the fan has not run this cycle
				if(debug): print "\tProactive fan has not ran this cycle.."
				if(log['current_temperature'] > log['target_temperature']): #Turn On Fan If Temp is above target temp
					if(debug): print "\t\tTemp is above the target temp.. Turnning on fan"
					log['proactive_fan_run']  = True
					controlData['fan_state'] = True
					##TEMP
					sendFanCommand(nest, "on")
					log['proactive_fan_run_time'] = 0
				else:
					if(debug): print "\t\tTemp is blow target.. Setting runtime to previous log value"
					log['proactive_fan_run_time'] = dayLog[index]['proactive_fan_run_time']
					log['proactive_fan_run'] = dayLog[index]['proactive_fan_run']

			elif(dayLog[index]['proactive_fan_run'] == True ): #Has the fan already ran? or is currently running
				if(debug): print "\tProactive fan has ran or is currently running for this cycle.."
				if(log['fan_state'] == True): #If fan is currently running - See if it has been running for 5 min - If so stop it. If it is not currently running.. Assume that it has already ran this cycle.
					if(debug): print "\t\tFan is currently running.. Calculating Fan Runtime for this cycle.."
					then = dateutil.parser.parse(dayLog[index]['$timestamp'])
					now = dateutil.parser.parse(log['$timestamp'])
					diff = now - then
					diff = diff.total_seconds()/60
					log['proactive_fan_run_time'] = dayLog[index]['proactive_fan_run_time'] + diff

					if(log['proactive_fan_run_time'] >= 5):
						if(debug): print "\t\t\tFan has been running for over 5 min.. turnning fan off..."
						log['proactive_fan_run'] = True
						controlData['fan_state'] = False
						#TEMP
						sendFanCommand(nest, "auto")
					else:
						if(debug): print "\t\t\tFan has been running for less than 5 min.. Leaving running.."
						if(debug): print "\t\t\t\tFan run time:", log['proactive_fan_run_time']
						log['proactive_fan_run'] = True

				else:
					if(debug): print "\t\tFan is off and has already ran this cycle.."
					log['proactive_fan_run_time'] = dayLog[index]['proactive_fan_run_time']
					log['proactive_fan_run'] = True




def sendFanCommand(nest, fan_state):
	nest.devices[0]._set('device', {"fan_mode": fan_state})

def sendTempCommand(nest, targetTemp):
	targetTemp = utils.f_to_c(targetTemp)
	nest.devices[0]._set('shared', {'target_temperature': targetTemp})



def sendControlData(controlData):
	print "Sending Control Data.."


#############
# MAIN
#############
def main(args):
	global debug
	global verbose
	global one_time_run
	global smartNestEnabled

	if(args.debug):
		debug = True
	if(args.verbose):
		verbose = True
	if(args.one_time_run):
		one_time_run = True
	if(args.smartnest):
		smartNestEnabled = True
	nestUser = User(username=args.username,password=args.password) #,filename=args.accountfile)
	myNest = nestAuth(nestUser)


	smartLoop(myNest)



#############
# END OF MAIN
#############

#############
# USER CLASS
#############
class User:
	def __init__(self,username=None,password=None,filename=None):
		self.username = username
		self.password = password
		self.filename = filename



###########################
# PROG DECLARE
###########################
if __name__ == '__main__':
	args = getArgs()
	main(args)
