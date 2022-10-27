from transfer_to_zenodo import Transfer_to_zenodo
from time import sleep
import sys

if __name__ == "__main__":
    # valid number of arguments is 1 or 2
    if 3 < len(sys.argv) < 2:
        print("Wrong number of arguments!")

    # 2 arguments means processing records in range
    if len(sys.argv) == 3:
        id_list = []
        with open("all_ids.txt") as f:
            id_list = list(f)
            id_list = [int(i) for i in id_list]

        for i in id_list:
            if int(sys.argv[1]) <= i < int(sys.argv[2]):
                transfer_object = Transfer_to_zenodo(i)
                transfer_object.get_record()
                transfer_object.upload_to_zenodo()
                sleep(3)

    # -2137 is a special code for cleaning upload service
    elif int(sys.argv[1]) == -2137:
        transfer_object = Transfer_to_zenodo(int(sys.argv[1]))
        transfer_object.delete_records()
    
    # single argument means uploading single record
    else:
        transfer_object = Transfer_to_zenodo(int(sys.argv[1]))
        transfer_object.get_record()
        transfer_object.upload_to_zenodo()

        # commented out for testing
        # transfer_object.post_record()
