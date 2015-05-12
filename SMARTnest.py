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

	# THREADING LOOP - EVERY 120 SECONDS
	if(not debug):
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




	#######################
	# SAVING DATA TO FILES
	#######################

	dayLog.append(log)

	try:
		pickle.dump(dayLog,open(log_filename,'wb'))
	except:
		print "Error Saving Log"


	# PRINT TO SCREEN IF IN DEBUG
	if(debug):
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
		if(log['ac_state'] == False and dayLog[index]['ac_state'] == False):
			log['total_run_time'] = dayLog[index]['total_run_time']
			log['total_run_time_home'] = dayLog[index]['total_run_time_home']
			log['total_run_time_away'] = dayLog[index]['total_run_time_away']
			log['trans_time'] = False
			log['total_trans_time'] = dayLog[index]['total_trans_time']
		else:
			then = dateutil.parser.parse(dayLog[index]['$timestamp'])
			now = dateutil.parser.parse(log['$timestamp'])
			diff = now - then
			diff = diff.total_seconds()/60
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
			elif(log['away'] == False and dayLog[index]['away'] == False and dayLog[index]['trans_time'] == True):
				log['trans_time'] = True
				log['total_trans_time'] = dayLog[index]['total_trans_time'] + diff
			else:
				log['trans_time'] = False
				log['total_trans_time'] = dayLog[index]['total_trans_time']

		if(log['away']):
			log['target_temperature'] = away_temp




def generateGraph(dayLog):

	timestamps = []
	total_run_time = []
	total_run_time_home = []
	total_run_time_away = []
	total_trans_time = []
	target_temperature = []
	current_temperature = []
	outside_temperature = []

	for log in dayLog:
		timestamps.append(log['$timestamp'])
		total_run_time.append(log['total_run_time'])
		total_run_time_home.append(log['total_run_time_home'])
		total_run_time_away.append(log['total_run_time_away'])
		total_trans_time.append(log['total_trans_time'])
		target_temperature.append(log['target_temperature'])
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
	line_chart.add('Inside Temperature', current_temperature)
	line_chart.add('Outside Temperature', outside_temperature)

	line_chart.render_to_file('daily.svg')  




#############
# MAIN
#############
def main(args):
	global debug
	if(args.debug):
		debug = True
	nestUser = User(username=args.username,password=args.password,filename=args.accountfile)
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


