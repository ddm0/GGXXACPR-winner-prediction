import os
import zlib
import csv
import enum

#A function that returns a length of bytes from the data given as an integer.
def b_read(data, offset, length):
    return int.from_bytes(data[offset:offset+length], byteorder="little")

#A function that returns a length of bytes from the data given as a signed integer.
def sb_read(data, offset, length):
    return int.from_bytes(data[offset:offset+length], byteorder="little", signed=True)

#An ENUM type for different possible errors.
class EType(enum.Enum):
    METADATA = 0 #Wrong metadata size
    OPTIONS = 1 #Custom options
    TEAM = 2 #Team mode
    AC = 3 #Old game version
    ROUNDS = 4 #Modified number of rounds in a match
    DRAW = 5 #The game ended in a draw
    FRAMES = 6 #Frame count error

#Setup error handling
filename = ""
error_list = [[""] for i in range(len(EType))]
error_count = [0] * len(EType)
total_error_count = 0

class Error(Exception):
    def __init__(self, error, msg):
        global error_list, error_count, total_error_count
        error_list[error.value].append(str(msg) + ", " + filename)
        error_count[error.value] += 1;
        total_error_count += 1;
        
#Setup offsets and sizes of the replay format
metadata_start = 26
metadata_size_pos = 12
frame_pos = 2312
frame_size = 260

character1_pos = 114
character2_pos = 115
extra_options_pos = 116
team_pos = 117
ac_pos = 118
rounds1_pos = 123
rounds2_pos = 124

path = "replay files/"

data = []
replay_count = 0

#Iterate through each replay
for filename in os.listdir(path):
    replay_count += 1

    #Print the current progress every 500th replay
    if replay_count % 500 == 0:
        print("Replay Count: " + str(replay_count))

    with open(path+filename, 'rb') as f:
        raw_data= f.read()

    #Read how long the metadata is
    metadata_size = b_read(raw_data, metadata_size_pos, 2)
    metadata_end = metadata_start+metadata_size

    try:
        #Error check if metadata is the right size
        #If it is smaller than 99 it could indicate an old replay format
        if metadata_size < 99:
            raise Error(EType.METADATA, metadata_size)

        #Verify that the replay has standard game settings
        if (v:=b_read(raw_data, extra_options_pos, 1)) != 0:
            raise Error(EType.OPTIONS, v)
        if (v:=b_read(raw_data, team_pos, 1)) != 1:
            raise Error(EType.TEAM, v)
        if (v:=b_read(raw_data, ac_pos, 1)) != 0:
            raise Error(EType.AC, v)

        #Get rounds won
        rounds1 = b_read(raw_data, rounds1_pos, 1)
        rounds2 = b_read(raw_data, rounds2_pos, 1)

        #Verify best of 3
        if not (((rounds1 == 2) and (rounds2 <= 2)) or ((rounds2 == 2) and (rounds1 <= 2))):
            raise Error(EType.ROUNDS, str(rounds1) + "/" + str(rounds2))
        
        #Verify no draw
        if (rounds1 == rounds2):
           raise Error(EType.DRAW, str(rounds1) + "/" + str(rounds2))

        #Determine winner
        match_result = 0
        if rounds2 == 2:
            match_result = 1
            
        #Get character values from the metadata
        character1 = b_read(raw_data, character1_pos, 1)
        character2 = b_read(raw_data, character2_pos, 1)
        
        #Decompress the replay data using zlib
        pos = metadata_end
        c_data = raw_data[pos:]
        d_data = zlib.decompress(c_data)

        #Get the number of savestates
        #4 bytes before the first savestate
        savestate_total = b_read(d_data, frame_pos-4, 4)

        #Ensure that the replay contains savestates by checking the first 5 frame counts
        pos = frame_pos
        for i in range(5):
            if b_read(d_data, pos, 2) % 60 != 0 or b_read(d_data, pos, 2) >= b_read(d_data, pos+frame_size, 2):
                raise Error(EType.FRAMES, str(i) + ", " + str(pos) + "/" + str(pos+frame_size) + ", " + str(b_read(d_data, pos, 2)) + "/" + str(b_read(d_data, pos+frame_size, 2)))
            pos += frame_size
            
      	#We now know that there are no errors in the replay file, and that the replay fits the requirements for being included in the dataset.
        #Now we iterate through the replay and save the replay data.
        pos = frame_pos
        for i in range(savestate_total):
            #Get the data for all of the savestate values that we want to include in the dataset
            data.append([match_result,
                        character1,
                        character2,
                        b_read(d_data,pos,4),
                        b_read(d_data,pos+4,4),
			b_read(d_data,pos+16,4),
                        b_read(d_data,pos+32,4),
                        b_read(d_data,pos+36,4),
                        b_read(d_data,pos+40,4),
                        b_read(d_data,pos+44,4),
                        sb_read(d_data,pos+48,4),
                        sb_read(d_data,pos+52,4),
                        b_read(d_data,pos+56,4),
                        b_read(d_data,pos+60,4),
                        b_read(d_data,pos+64,4),
                        sb_read(d_data,pos+68,4),
                        sb_read(d_data,pos+72,4),
                        sb_read(d_data,pos+76,4),
                        sb_read(d_data,pos+80,4),
                        b_read(d_data,pos+84,4),
                        b_read(d_data,pos+88,4),
                        b_read(d_data,pos+92,4),
                        b_read(d_data,pos+96,4),
                        b_read(d_data,pos+100,4),
                        b_read(d_data,pos+104,4)])
            
            pos += frame_size
    
    except Error:
        pass

        

#Write invalid replay statistics
with open("invalid_replays.txt", 'w', encoding="utf-8") as f:
    f.write("Excluded replays: " + str(total_error_count) + " out of " + str(replay_count) + "\n\n")

    for etype in EType:
        f.write(str(etype) + ": " + str(error_count[etype.value]) + "\n")
        for error in error_list[etype.value]:
            f.write(error + "\n")
        f.write("\n")


#Write valid replay data to a csv file
data_fields = ["MatchResult",
         "Character1",
         "Character2",
         "Frame",
         "MatchCountdown",
         "MT Value",
         "Action1",
         "Action2",
         "Burst1",
         "Burst2",
         "Guard1",
         "Guard2",
         "Health1",
         "Health2",
         "RoundTimer",
         "PosX1",
         "PosX2",
         "PosY1",
         "PosY2",
         "RoundsWon1",
         "RoundsWon2",
         "Stun1",
         "Stun2",
         "Tension1",
         "Tension2"]
    
with open("replay_data.csv", 'w', newline='') as f:
    csv_write = csv.writer(f)
    csv_write.writerow(data_fields)
    csv_write.writerows(data)
