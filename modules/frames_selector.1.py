from MDAnalysis import Universe
import MDAnalysis.lib.distances as distanceslib
from numpy import min#, mean, array, max
import sys
import os
from progressbar import ProgressBar, Percentage, Bar, ETA, Timer
import copy
import shutil


def ask(argsdict):
    '''
    Function that asks for atom indexes (the atoms which will be used for stablishing the criteria of selection).
    It lets compare atoms between them so only the shortest distance is used.
    It aks also for the cut-off.
    Returns the \'atoms_list\' and the \'cut_off\' values.
    '''
    
    while True:
        try :
            prot_atoms = [int(input("Input the number of one of the selected atoms for measuring distances. "))]
            break
        except ValueError:
            print('The atom\'s number has not been correctly introduced.\n')
            continue

    while True:
        try :
            subs_atoms_input = input("Input the number of the atom(s) for measuring distances (separate by a comma if you want to consider only the nearest one). ")
            if subs_atoms_input.find(',') != -1:
                subs_atoms = subs_atoms_input.split(',')
                for i in range(0, len(subs_atoms)):
                    subs_atoms[i] = int(subs_atoms[i])
            else :
                subs_atoms = [int(subs_atoms_input)]
            break
        except ValueError:
            print('(Some of) the number(s) of the atom(s) has not been correctly introduced.\n')
            continue
    atoms_list = [prot_atoms, subs_atoms]

    u_top = Universe(argsdict['parameters'])
    quest = None

    while True:
        print("\nYou have selected those atoms:\n")
        ### Print selected atoms (number, name, type, resname an resid) and save names
        exists = []
        for i in range(0, len(atoms_list)):
            name = None
            for j in range(0, len(atoms_list[i])):
                a = str(u_top.select_atoms("bynum %s" % atoms_list[i][j]))
                exists.append(a.find('AtomGroup []') != -1)
                locA = a.find('[<') +2
                locB = a.find(' and')
                if name == None:
                    name = '\t' + a[locA:locB]
                else :
                    name = name +'; ' + a[locA:locB]
            print(name)
        print("\n")

        if True in exists:
            print('Some of the specified atom doesn\'t exist. Enter the atom numbers again.\n')
            quest = 'no'
            del exists
        else :
            quest = str(input("Are all numbers correct ([y]/n)?"))

        if quest in ('n', 'no', 'N', 'No', 'No', 'nO', '0'):
            while True:
                try :
                    prot_atoms = [int(input("Input the number of one of the selected atoms for measuring distances. "))]
                    break
                except ValueError:
                    print('The atom\'s number has not been correctly introduced.\n')
                    continue

            while True:
                try :
                    subs_atoms_input = input("Input the number of the atom(s) for measuring distances (separate by a comma if you want to consider only the nearest one). ")
                    if subs_atoms_input.find(',') != -1:
                        subs_atoms = subs_atoms_input.split(',')
                        for i in range(0, len(subs_atoms)):
                            subs_atoms[i] = int(subs_atoms[i])
                    else :
                        subs_atoms = [int(subs_atoms_input)]
                    break
                except ValueError:
                    print('(Some of) the number(s) of the atom(s) has not been correctly introduced.\n')
                    continue
            atoms_list = [prot_atoms, subs_atoms]
            continue

        elif quest in ('', 'y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
            break
        else :
            print("Sorry, answer again, please.")
            continue
        break


    while True:
        try :
            cut_off = float(input("Type the cut-off distance (in Å): "))
            break
        except ValueError:
            print("The cut-off distance has not been well specified. Please, retype the cut-off distance.")
            continue

    return atoms_list, cut_off


def bool_creator(u, argsdict, atoms_list, cut_off):
    '''
    Using the \'atoms_list\' and the \'cut_off\', it calculates the distances between the selected atoms and compares it
    (or the shortest if comparison is required) to the  \'cut_off\' distance. If the computed distance is shortest or equal
    to the \'cut_off\' distance, it saves \'True\' to a boolean list. If the distance is grater, \'False\' is saved.
    Finally, if more than one criteria is specified, it will compare the obtained boolean arrays.
    '''
    if argsdict['u_loaded'] == False:
        from modules import loader
        u, argsdict = loader.universe_loader_traj(argsdict)

    atoms_sel = []; sel_bool_ = []
    for i in range(0, len(atoms_list)):
        sel_bool_.append([])
        atoms_sel.append([[],[]])
        atoms_sel[i][0] = u.select_atoms('bynum %s' % atoms_list[i][0][0])
        sel_ = None
        for j in range(0, len(atoms_list[i][1])):
            if sel_ == None:
                sel_ = 'bynum %s' % atoms_list[i][1][j]
            else :
                sel_ = sel_ + ' or bynum %s' % atoms_list[i][1][j]
        atoms_sel[i][1] = u.select_atoms(sel_)
        del sel_

    time_ = 0
    widgets = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'),
           ' ', ETA(), ' | ', Timer(), ' ']

    pbar = ProgressBar(widgets=widgets, maxval=len(u.trajectory))
    pbar.start()

    for ts in u.trajectory:
        time_+=1

        for i in range(0, len(atoms_sel)):
            if argsdict['parallel'] == False:
                dist_ = min(distanceslib.distance_array(atoms_sel[i][0].positions, atoms_sel[i][1].positions, backend='serial'))
            elif argsdict['parallel'] == True:
                dist_ = min(distanceslib.distance_array(atoms_sel[i][0].positions, atoms_sel[i][1].positions, backend='OpenMP'))

            if dist_ <= cut_off[i]:
                sel_bool_[i].append(True)
            elif dist_ > cut_off[i]:
                sel_bool_[i].append(False)

        pbar.update(time_)

    pbar.finish()

    sel_bool = []
    if len(sel_bool_) == 1:
        #for i in range(len(sel_bool_)):
        sel_bool = copy.deepcopy(sel_bool_[0])
    elif len(sel_bool_) > 1:
        for i in range(len(u.trajectory)):
            bool_ = []
            for j in range(len(sel_bool_)):
                bool_.append(sel_bool_[j][i])
            if False in bool_:
                sel_bool.append(False)
            elif False not in bool_:
                sel_bool.append(True)
        del bool_
    del sel_bool_

    print("\nThe " + str(round((sel_bool.count(True)/len(sel_bool) * 100), 4)) + '% of the frames satisfy the specified criteria.\n')

    #print(atoms_sel)
    #for i in range(len(atoms_sel)):
    #    for j in range(len(atoms_sel[i])):
    #        print(atoms_sel[i][j])

    return u, argsdict, sel_bool


def txt_saver(sel_bool, atoms_list, cut_off):

    txt_name = ''
    for i in range(len(atoms_list)):
        txt_name = txt_name + '_' + str(atoms_list[i][0][0]) + '_' + str(cut_off[i])

    if txt_name in os.listdir():
        while True:
            quest = input("A previous summary of the frame selection exists. Do you want to overwrite it (1) or to give a new name (2)? ([1]/2) ")
            if quest == '1' or quest == '':
                break
            elif quest == '2':
                while True:
                    txt_name = input('Type the new name for the summary file: ')
                    quest2 = input('Is \'%s\' correct? ([y]/n) ' % txt_name)
                    if quest2 in ('', 'y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
                        break
                    elif quest2 in ('n', 'no', 'N', 'No', 'NO', 'nO', '0'):
                        continue
                break
            else :
                print('Type just \'1\' or \'2\'.')
                continue

    print('Summary file is being saved as \'%s\'.' % txt_name)

    txt_ext_name = ''
    for i in range(len(atoms_list)):
        txt_ext_name = txt_ext_name + '_' + str(atoms_list[i][0][0]) + '_' + str(cut_off[i])

        if txt_ext_name in os.listdir():
            while True:
                quest = input("A previous extended summary of the frame selection exists. Do you want to overwrite it (1) or to give a new name (2)? ([1]/2) ")
                if quest == '1' or quest == '':
                    break
                elif quest == '2':
                    while True:
                        txt_ext_name = input('Type the new name for the extended summary file: ')
                        quest2 = input('Is \'%s\' correct? ([y]/n) ' % txt_ext_name)
                        if quest2 in ('', 'y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
                            break
                        elif quest2 in ('n', 'no', 'N', 'No', 'NO', 'nO', '0'):
                            continue
                    break
                else :
                    print('Type just \'1\' or \'2\'.')
                    continue

    print('Extended summary file is being saved as \'%s\'.' % txt_ext_name)

    txt = open(txt_name, 'w')
    txt_ext = open(txt_ext_name, 'w')

    for i in range(len(sel_bool)):
        if sel_bool[i] == True:
            txt.write('Frame %s satisfies the imposed criteria\n' % (i+1))
            txt_ext.write('Frame %s satisfies the imposed criteria\n' % (i+1))
        elif sel_bool[i] == False:
            txt_ext.write('Frame %s does not satisfy the imposed criteria\n' % (i+1))

    T = (sel_bool.count(True)/len(sel_bool)) * 100
    F = (sel_bool.count(False)/len(sel_bool)) * 100

    txt.write('\n\nThe %s %% satisfy the imposed criteria.' % T)
    txt.write('\nThe %s %% do not satisfy the imposed criteria.' % F)

    txt_ext.write('\n\nThe %s %% satisfy the imposed criteria.' % T)
    txt_ext.write('\nThe %s %% do not satisfy the imposed criteria.' % F)

    txt.close()
    txt_ext.close()


def pdb_saver_all(u, sel_bool, atoms_list, cut_off):
    '''
    Function for saving the pdbs of all the frames which satisfy the imposed criteria.
    '''

    dir_name = 'frames'
    for i in range(len(atoms_list)):
        dir_name = dir_name + '_' + str(atoms_list[i][0][0]) + '_' + str(cut_off[i])

    if dir_name not in os.listdir():
        os.mkdir(dir_name)
        #print(dir_name)
    elif dir_name in os.listdir():
        while True:
            quest = input('%s subdirectory aready exists. Do you want to overwrite its content (1) or give an alternative name to the subdirectory (2)? ([1]/2) ' % dir_name)
            if quest in ('1', '2', ''):
                if quest in ('', '1'):
                    shutil.rmtree(dir_name)
                    os.mkdir(dir_name)
                    break
                elif quest == '2':
                    while True:
                        dir_name = input('Type the new name of the subdirectory: ')
                        quest2 = input('Is \'%s\' correct? ([y]/n) ' % dir_name)
                        if quest2 in ('', 'y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
                            break
                        elif quest2 in ('n', 'no', 'N', 'No', 'NO', 'nO', '0'):
                            continue

                    if dir_name not in os.listdir():
                        break
                    elif dir_name in os.listdir():
                        continue

            elif quest not in ('1', '2', ''):
                print('Choose 1 or 2.')
                continue

    time_ = 0
    widgets2 = ['Progress: ', Percentage(), ' ', Bar(marker='#',left='[',right=']'),
           ' ', ETA(), ' | ', Timer(), ' ']

    pbar2 = ProgressBar(widgets=widgets2, maxval=len(sel_bool))
    pbar2.start()

    stderr_ = open(os.devnull, 'w')
    sys.stderr = stderr_

    for i in range(len(sel_bool)):
        time_+=1
        if sel_bool[i] == True:
            u.trajectory[i]
            sel = u.select_atoms('all')
            sel.write('%s/frame_%s.pdb' % (dir_name, (i+1)))

        pbar2.update(time_)

    pbar2.finish()
    stderr_.close()


def pdb_saver_some(u, sel_bool, atoms_list, cut_off):
    '''
    Function for saving the pdbs of the selected frames which satisfy the imposed criteria.
    '''

    dir_name = 'frames'
    for i in range(len(atoms_list)):
        dir_name = dir_name + '_' + str(atoms_list[i][0][0]) + '_' + str(cut_off[i])

    if dir_name not in os.listdir():
        os.mkdir(dir_name)
        #print(dir_name)
    elif dir_name in os.listdir():
        while True:
            quest = input('%s subdirectory aready exists. Do you want to overwrite its content (1) or give an alternative name to the subdirectory (2)? ([1]/2) ' % dir_name)
            if quest in ('1', '2', ''):
                if quest in ('', '1'):
                    shutil.rmtree(dir_name)
                    os.mkdir(dir_name)
                    break
                elif quest == '2':
                    while True:
                        dir_name = input('Type the new name of the subdirectory: ')
                        quest2 = input('Is \'%s\' correct? ([y]/n) ' % dir_name)
                        if quest2 in ('', 'y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
                            break
                        elif quest2 in ('n', 'no', 'N', 'No', 'NO', 'nO', '0'):
                            continue

                    if dir_name not in os.listdir():
                        break
                    elif dir_name in os.listdir():
                        continue

            elif quest not in ('1', '2', ''):
                print('Choose 1 or 2.')
                continue

    stderr_ = open(os.devnull, 'w')
    sys.stderr = stderr_

    while True:
        try :
            frame_n = str(input('Which frame do you want to save as pdb? (type \'list\' to show a list of frame to select) '))

            if frame_n in ('list', 'LIST', 'List', 'lIST', 'LIst', 'liST', 'LISt', 'lisT'):
                print_ = ''
                for i in range(len(sel_bool)):
                    if sel_bool[i] == True:
                        if print_ == '':
                            print_ = str(int(i+1))
                        else :
                            print_ = print_ + ', ' + str(int(i+1))

                print(print_); del print_
                continue

            elif frame_n == '':
                print('Type the number.')
                continue

            else :
                frame_n = int(frame_n) -1
                if sel_bool[frame_n] == True:
                    u.trajectory[frame_n]
                    sel = u.select_atoms('all')
                    sel.write('%s/frame_%s.pdb' % (dir_name, (frame_n+1)))
                    print('Frame %s saved on %s.' % ((frame_n+1), dir_name))
                    break

                elif sel_bool[frame_n] == False:
                    print('This frame does not satisfy the imposed criteria. Please, select another frame. (Type \'list\' to print the list of frames that satisfy the imposed criteria)')
                    continue

        except TypeError:
            print('Type only the number.')

    while True:
        try :
            frame_n = str(input('Do you want to save another frame as pdb? (frame number/[n])'))

            if frame_n in ('list', 'LIST', 'List', 'lIST', 'LIst', 'liST', 'LISt', 'lisT'):
                print_ = ''
                for i in range(len(sel_bool)):
                    if sel_bool[i] == True:
                        if print_ == '':
                            print_ = str(int(i+1))
                        else :
                            print_ = print_ + ', ' + str(int(i+1))

                print(print_); del print_
                continue

            elif frame_n in ('', 'n', 'no', 'N', 'No', 'NO', 'nO', '0'):
                break

            else :
                frame_n = int(frame_n-1)
                if sel_bool[frame_n] == True:
                    u.trajectory[frame_n]
                    sel = u.select_atoms('all')
                    sel.write('%s/frame_%s.pdb' % (dir_name, (frame_n+1)))
                    continue

                elif sel_bool[frame_n] == False:
                    print('This frame does not satisfy the imposed criteria. Please, select another frame. (Type \'list\' to print the list of frames that satisfy the imposed criteria)')
                    continue

        except TypeError:
            print('Type only the number.')

    stderr_.close()


def frame_selector(u, argsdict):

    atoms_list = []; cut_off = []
    atoms_list_, cut_off_ = ask(argsdict)

    atoms_list.append(atoms_list_)
    cut_off.append(cut_off_)

    while True:
        quest = input("Do you want to add another distance criteria for selecting frames (y/[n])? ")
        if quest in ('', 'n', 'no', 'N', 'No', 'No', 'nO', '0'):
            break
        elif quest in ('y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
            atoms_list_, cut_off_ = ask(argsdict)
            atoms_list.append(atoms_list_)
            cut_off.append(cut_off_)
            continue
        else :
            print("Sorry, answer again, please.")
            continue

    u, argsdict, sel_bool = bool_creator(u, argsdict, atoms_list, cut_off)

    while True:
        quest = input('Do you want to save a summary of the selection results ([y]/n)? ')
        if quest in ('', 'y', 'yes', 'Y', 'YES', 'Yes', 'yES', 'YeS', 'yEs', 'YEs', '1'):
            txt_saver(sel_bool, atoms_list, cut_off)
            break
        elif quest in ('n', 'no', 'N', 'No', 'NO', 'nO', '0'):
            break
        else :
            print('Please, answer \'yes\' or \'no\'.')
            continue

    while True:
        try :
            quest = int(input('Do you want to save all the frames (1), the selected ones (2) or any of them (3)? '))

            if quest == 1:
                pdb_saver_all(u, sel_bool, atoms_list, cut_off)
                break

            elif quest == 2:
                pdb_saver_some(u, sel_bool, atoms_list, cut_off)
                break

            elif quest == 3:
                break

            else :
                print('Type 1, 2 or 3')
                continue

        except ValueError:
            print('Type 1, 2 or 3')
            continue

    #del atoms_list; del cut_off; del atoms_list_; del cut_off_
    return u, argsdict
