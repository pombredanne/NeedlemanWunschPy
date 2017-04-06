#!/usr/bin/env python

import logging
import numpy as np
import pandas as pd
from Bio.SubsMat import MatrixInfo

# About
__author__ = "Antonio Benitez Hidalgo"
__email__ = "antonio.b@uma.es"
__version__ = "1.0-SNAPSHOT"

# Logger for debug
LOG_FILENAME = 'log.txt'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("log.log", mode='w')
formatter = logging.Formatter('%(asctime)s - %(name)-5s - %(levelname)-5s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


"""
 Global alignment with simple gap costs using the Needleman-Wunsch algorithm.

 Note: The pseudo-code implemented in this example can be found here:
            http://www.inf.fu-berlin.de/lehre/WS05/aldabi/downloads/pairAlign_part1.pdf
 More info: https://ab.inf.uni-tuebingen.de/teaching/ws06/albi1/script/pairalign_script.pdf,
            http://www.itu.dk/people/sestoft/bsa/graphalign.html
"""


class NeedlemanWunsch():

    # TODO: Tests need to be implemented for this class
    # TODO: "cythonize" the code in order to improve performance ( http://cython.readthedocs.io/en/latest/index.html )

    def __init__(self, seqA, seqB, gap_penalty, substitution_matrix):
        self.seq_h = seqA  # seq A (horizontal, rows)
        self.seq_v = seqB  # seq B (vertical, columns)
        self.gap_penalty = gap_penalty  # gap penalty both for opening and extension (linear gap penalty)
        self.substitution_matrix = substitution_matrix

        self.num_rows = len(seqA) + 1  # number of rows plus one (the first one)
        self.num_cols = len(seqB) + 1  # number of columns plus one (the first one)

        # Initialization of both matrices of zeros
        self.M = np.zeros(shape=(self.num_cols, self.num_rows), dtype=np.int)  # matrix of zeros of integers (score matrix)
        self.T = np.zeros(shape=(self.num_cols, self.num_rows), dtype=np.str)  # matrix of zeros of strings (traceback matrix)

        # Alignment sequences
        self.seqaln_h = ""
        self.seqaln_v = ""
        self.aln_score = 0

    def get_score(self, char1, char2):
        """ Get score from the substitution matrix.

        :return: Score of the pair of chars.
        """

        if char1 is '-' and char2 is '-':
            result = 1
        elif char1 is '-' or char2 is '-':
            result = self.gap_penalty
        else:  # Note that the substitution matrix is triangular
            if (char1, char2) in self.substitution_matrix:
                v = self.substitution_matrix[char1, char2]
            else:
                v = self.substitution_matrix[char2, char1]
            result = v

        return result

    def scoring_and_traceback_matrices(self):
        """ Needleman Wunsch algorithm. Formula:
                M(0,0) = 0
                M(i,0) = M(i-1,0) - gap_penalty
                M(0,j) = M(0,j-1) - gap_penalty
                M(i,j) = max{ M(i-1,j-1) + score , M(i-1,j) - penalty, M(i,j-1) - penalty }

            M will be our scoring matrix.
            T will be our traceback matrix.
        """

        # First column and row
        self.M[0, 0] = 0
        self.T[0, 0] = "•"
        for i in range(1, self.num_cols):  # First row
            self.M[i, 0] = self.M[i - 1, 0] - self.gap_penalty
            self.T[i, 0] = "↑"
        for j in range(1, self.num_rows):  # First column
            self.M[0, j] = self.M[0, j - 1] - self.gap_penalty
            self.T[0, j] = "←"

        # Rest of the matrix (recursive)
        for i in range(1, self.num_cols):
            for j in range(1, self.num_rows):
                current_score = self.get_score(self.seq_h[j - 1], self.seq_v[i - 1])
                score_diagonal = self.M[i - 1, j - 1] + current_score
                score_up = self.M[i - 1, j] - self.gap_penalty
                score_left = self.M[i, j - 1] - self.gap_penalty
                max_score = max(score_diagonal, score_up, score_left)

                self.M[i, j] = max_score

                # Arrows in the traceback matrix (T) indicating which cell each score was derived
                if max_score == score_diagonal:
                    self.T[i, j] = '↖'
                elif max_score == score_up:
                    self.T[i, j] = '↑'
                else:
                    self.T[i, j] = '←'

        logger.debug("Saving matrices into .csv files...")
        self.save_matrix_to_file(self.M, 'scoring_matrix')
        self.save_matrix_to_file(self.T, 'traceback_matrix')
        logger.debug("...OK.")

    def save_matrix_to_file(self, matrix, filename):
        """ Save matrix dataframe into a .csv file separated by commas.

        :param matrix: Numpy matrix.
        :param filename: Name of the file.
        """

        data = pd.DataFrame(matrix, index=list(' ' + self.seq_v), columns=list(' ' + self.seq_h))
        data.to_csv(filename+'.csv', sep=',', encoding='utf-8')

    def traceback(self):
        """ Traceback algorithm. We can make the traceback looking to the traceback matrix (T):
            ...up arrow: we consume a character from the vertical sequence and add a gap to the horizontal one
            ...left arrow: we consume a character from the horizontal sequence and add a gap to the vertical one
            ...diagonal arrow: we consume a character from both sequences.
        """

        alnseqA, alnseqB, path = [], [], []
        i, j = self.num_cols - 1, self.num_rows - 1

        while i > 0 or j > 0:
            score_diagonal = self.M[i - 1, j - 1] + self.get_score(self.seq_h[j - 1], self.seq_v[i - 1])
            score_up = self.M[i - 1, j] - self.gap_penalty
            score_left = self.M[i, j - 1] - self.gap_penalty
            max_score = max(score_diagonal, score_up, score_left)

            logger.debug("max score: {0}, score diagonal: {1}, score up: {2}, score left: {3}".format(max_score,
                                                                                                      self.M[i-1, j-1],
                                                                                                      self.M[i-1, j],
                                                                                                      self.M[i, j-1]))

            if i > 0 and j > 0 and max_score == score_diagonal:
                logger.debug(" > going diagonal")
                alnseqA.append(self.seq_v[i - 1])
                alnseqB.append(self.seq_h[j - 1])
                path.append(self.M[i, j])
                i, j = i-1, j-1
            elif i > 0 and max_score == score_up:
                logger.debug(" > going up")
                alnseqA.append(self.seq_v[i - 1])
                alnseqB.append('-')
                path.append(self.M[i, j])
                i -= 1
            elif max_score == score_left:
                logger.debug(" > going left")
                alnseqA.append('-')
                alnseqB.append(self.seq_h[j - 1])
                path.append(self.M[i, j])
                j -= 1

        # Finish tracing up to the top left cell
        while i > 0:
            alnseqA.append(self.seq_v[i - 1])
            alnseqB.append('-')
            path.append(self.M[i, j])
            i -= 1
        while j > 0:
            alnseqA.append('-')
            alnseqB.append(self.seq_h[j - 1])
            path.append(self.M[i, j])
            j -= 1

        # Return both reversed alignment sequences
        self.seqaln_h, self.seqaln_v = "".join(alnseqA)[::-1], "".join(alnseqB)[::-1]
        logger.debug('Pathway chosen in the traceback matrix: {0}'.format(path))

    def totally_conserved_columns(self):
        """ Method for getting the position of the totally conserved columns.

        :return: String with vertical bars in those places were the columns are totally conserved.
        """

        totally_conserved_columns = []

        for k in range(len(self.seqaln_h)):
            if self.seqaln_h[k] == self.seqaln_v[k]:
                totally_conserved_columns.append('|')
            else:
                totally_conserved_columns.append(' ')

        logger.debug("Number of totally conserved columns: {0}".format(totally_conserved_columns.count('|')))

        return "".join(totally_conserved_columns)

    def get_score_of_alignment(self):
        # TODO: This method will be implemented in future releases.
        pass


def main():
    # TODO: Import sequences from .FASTA files

    # Initialization
    seqA = "AAARHEAATAAAARST"
    seqB = "ARADHAAT"
    gap_penalty = 8  # in this case, gap penalty must be a positive int
    substitution_matrix = MatrixInfo.blosum50  # avaliable matrices: biopython.org/DIST/docs/api/Bio.SubsMat.MatrixInfo-module.html

    # Create the alignment
    aln = NeedlemanWunsch(seqA, seqB, gap_penalty, substitution_matrix)

    # Run algorithms
    logger.info("Running algorithms...")
    aln.scoring_and_traceback_matrices()
    aln.traceback()
    logger.debug("...OK.")

    # Print alignments along with the totally conserved columns
    print("[SEQUENCE1] {0}".format(aln.seqaln_v))
    print("[CONSERVED] {0}".format(aln.totally_conserved_columns()))
    print("[SEQUENCE2] {0}".format(aln.seqaln_h))

    # Save to file
    with open('traceback.txt', 'w') as output:
        output.write('[SEQUENCE1] '+aln.seqaln_v + '\n' +
                     '[CONSERVED] '+aln.totally_conserved_columns() + '\n' +
                     '[SEQUENCE2] '+aln.seqaln_h)


if __name__ == '__main__':
    main()