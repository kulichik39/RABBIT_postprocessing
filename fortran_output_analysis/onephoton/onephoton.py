import os
import numpy as np

from fortran_output_analysis.common_utility import (
    l_from_kappa,
    j_from_kappa,
    j_from_kappa_int,
    Hole,
    load_raw_data,
    l_to_str,
    construct_hole_name,
)


class IonisationPath:
    """
    Stores information about an ionisation path in the one photon case.
    """

    def __init__(self, kappa, col_idx):
        """
        Params:
        kappa - kappa value of the final state
        col_idx - index of the column in the raw data files corresponding to this
        final state
        """
        self.kappa = kappa
        self.l = l_from_kappa(kappa)
        self.j = j_from_kappa(kappa)
        self.name = l_to_str(self.l) + ("_{%i/2}" % (j_from_kappa_int(kappa)))
        self.column_index = col_idx


def final_kappas(hole_kappa, only_reachable=True):
    """
    Returns the possible final kappas that can be reached with one photon from
    an initial state with the given kappa. If only_reachable is False, this function
    will always return a list of three elements, even if one of them is 0.

    Params:
    hole_kappa - kappa value of the hole
    only_reachable - tells if only permitted states should be returned

    Returns:
    kappas - list with kappa values of possible final states
    """
    mag = np.abs(hole_kappa)
    sig = np.sign(hole_kappa)

    kappas = [sig * (mag - 1), -sig * mag, sig * (mag + 1)]

    if only_reachable:
        # Filter out any occurence of final kappa = 0
        kappas = [kappa for kappa in kappas if kappa != 0]

    return kappas


class Channels:
    """
    For the given hole, idenitifies possible ionization channels and loads raw Fortran data for
    them in the one photon case.
    """

    def __init__(
        self,
        path_to_omega,
        path_to_pcur,
        path_to_amp_all,
        path_to_phaseF_all,
        path_to_phaseG_all,
        hole: Hole,
    ):
        """
        Params:
        path_to_omega - path to the omega.dat file for the given hole (usually in
        pert folders)
        path_to_pcur - path to file with probabilty current for one photon
        path_to_amp_all - path to file with amplitudes for one photon
        path_to_phaseF_all - path to file with the phase for larger relativistic component
        of the wave function
        path_to_phaseG_all - path to file with the phase for smaller relativistic component
        of the wave function
        hole - object of the Hole class containing hole's parameters
        """

        self.__hole = hole
        self.__ionisation_paths = {}
        self.__add_ionisation_path()
        self.__raw_omega_data = load_raw_data(path_to_omega)
        raw_rate_data = load_raw_data(path_to_pcur)
        self.__raw_rate_data = raw_rate_data[:, 1:]  # skip the first column with omegas
        raw_amp_data = load_raw_data(path_to_amp_all)
        self.__raw_amp_data = raw_amp_data[:, 1:]
        raw_phaseF_data = load_raw_data(path_to_phaseF_all)
        self.__raw_phaseF_data = raw_phaseF_data[:, 1:]
        raw_phaseG_data = load_raw_data(path_to_phaseG_all)
        self.__raw_phaseG_data = raw_phaseG_data[:, 1:]

    def __add_ionisation_path(self):
        """
        Adds possbile hole's ionization paths. Excludes forbidden channels with
        kappa = 0.
        """
        kappa_hole = self.__hole.kappa
        # One can convince oneself that the following is true for a given hole_kappa.
        #       possible_final_kappas = np.array([-kappa_hole, kappa_hole+1, -(-kappa_hole+1)])
        # It is possible that one of the final kappas are zero, so we need to handle this.
        # NOTE(anton): The pcur-files have three columns, one for each possible final kappa.
        # If there is no possibility for one of them the column is zero, and I
        # think the convention is that the zero column is the left-most (lowest index) then.
        # So if the kappas are sorted by ascending absolute value we should get this, since
        # if kappa = 0 the channel is closed.
        #       sort_kappas_idx = np.argsort(np.abs(possible_final_kappas))
        #       possible_final_kappas = possible_final_kappas[sort_kappas_idx]

        # This code should reproduce the previous implementation
        possible_final_kappas = final_kappas(
            kappa_hole, only_reachable=False
        )  # list of ALL final states

        reachable_final_kappas = final_kappas(
            kappa_hole, only_reachable=True
        )  # list of reachable final states

        # This is for getting the data from the pcur files. The first column is the photon energy.
        column_index = 0
        for kappa in possible_final_kappas:
            if kappa in reachable_final_kappas:
                self.__ionisation_paths[kappa] = IonisationPath(kappa, column_index)

            column_index += 1

    def get_all_ionisation_paths(self):
        """
        Returns:
        all loaded ionisation paths
        """

        return self.__ionisation_paths

    def get_ionisation_path(self, final_kappa):
        """
        Returns ionisation paths for the given final kappa.

        Params:
        final_kappa - kappa value of the final state

        Returns:
        ionisation_path - object of the IonisationPath class
        """

        self.assert_ionisation_path(final_kappa)

        return self.__ionisation_paths[final_kappa]

    def assert_ionisation_path(self, final_kappa):
        """
        Assertion of the ionisation path. Checks if the given final kappa
        is within possible ionization paths.

        Params:
        final_kappa - kappa value of the final state
        """

        assert self.check_ionisation_path(
            final_kappa
        ), f"The state with final kappa {final_kappa} is not within ionisation paths for {self.__hole.name} hole!"

    def check_ionisation_path(self, final_kappa):
        """
        Checks if the given ionisation path (determined by final_kappa)
        is within self.__ionisation_paths.

        Params:
        final_kappa - kappa value of the final state

        Returns:
        True if the final state is within ionization paths, False otherwise.
        """

        return final_kappa in self.__ionisation_paths

    def get_raw_omega_data(self):
        """
        Returns:
        raw photon energies in Hartree
        """
        return self.__raw_omega_data

    def get_raw_amp_data(self, final_kappa):
        """
        Returns raw amplitude data for the given ionisation path (determined by final_kappa).

        Params:
        final_kappa - kappa value of the final state

        Returns:
        raw amplitudes data
        """

        ionisation_path = self.get_ionisation_path(final_kappa)
        column_index = ionisation_path.column_index

        return self.__raw_amp_data[:, column_index]

    def get_raw_phaseF_data(self, final_kappa):
        """
        Returns raw phase of the larger component for the given ionisation path
        (determined by final_kappa).

        Params:
        final_kappa - kappa value of the final state

        Returns:
        raw phase of the larger component
        """

        ionisation_path = self.get_ionisation_path(final_kappa)
        column_index = ionisation_path.column_index

        return self.__raw_phaseF_data[:, column_index]

    def get_raw_phaseG_data(self, final_kappa):
        """
        Returns raw phase of the smaller component for the given ionisation path
        (determined by final_kappa).

        Params:
        final_kappa - kappa value of the final state

        Returns:
        raw phase of the smaller component
        """

        ionisation_path = self.get_ionisation_path(final_kappa)
        column_index = ionisation_path.column_index

        return self.__raw_phaseG_data[:, column_index]

    def get_raw_rate(self, final_kappa):
        """
        Returns raw probability current for the given ionisation path (determined by final_kappa).

        Params:
        final_kappa - kappa value of the final state

        Returns:
        raw probability current
        """

        ionisation_path = self.get_ionisation_path(final_kappa)
        column_index = ionisation_path.column_index

        return self.__raw_rate_data[:, column_index]

    def get_hole_object(self):
        """
        Returns:
        the Hole object corresponding to these channels.
        """

        return self.__hole


class OnePhoton:
    """
    Grabs and stores data from Fortran simulations in the one photon case.
    """

    # TODO: remove g_omega_IR from initialisation and put it as parameter to corresponding functions
    def __init__(self, atom_name, g_omega_IR):
        # attributes for diag data
        self.__diag_eigenvalues = None
        self.__diag_matrix_elements = None
        self.__diag_loaded = False  # tells whether diagonal data was loaded

        # attributes for holes' data
        self.atom_name = atom_name
        self.__channels = {}
        self.num_channels = 0

        # energy of the IR photon used in Fortran simulations (in Hartree)
        self.g_omega_IR = g_omega_IR

    def load_diag_data(
        self,
        path_to_data,
        path_to_diag_eigenvalues=None,
        path_to_diag_matrix_elements=None,
        should_reload=False,
    ):
        """
        Loads diagonal data: eigenvalues and matrix elements, and saves them
        to the corresponding object attributes: self.__diag_eigenvalues and
        self.__diag_matrix_elements.

        Params:
        path_to_data - path to the output folder with Fortran simulation results
        path_to_diag_eigenvalues - path to the file with diagonal eigenvalues
        path_to_diag_matrix_elements - path to the file with diagonal matrix elements
        should_reload - tells whether we should reload diagonal data if they
        were previously loaded
        """

        if not self.__diag_loaded or should_reload:
            if self.__diag_loaded and should_reload:
                print(
                    f"Reload diagonal matrix elements and eigenvalues in {self.atom_name}!"
                )

            # if the paths to diag data are not specified, we assume that they are
            # in the output data folder
            if not path_to_diag_eigenvalues:
                path_to_diag_eigenvalues = path_to_data + "diag_eigenvalues_Jtot1.dat"

            if not path_to_diag_matrix_elements:
                path_to_diag_matrix_elements = (
                    path_to_data + "diag_matrix_elements_Jtot1.dat"
                )

            self.__load_diag_eigenvalues(path_to_diag_eigenvalues)
            self.__load_diag_matrix_elements(path_to_diag_matrix_elements)
            self.__diag_loaded = True

    def __load_diag_eigenvalues(self, path_to_diag_eigenvalues):
        """
        Loads diagonal eigenvalues and saves them to self.__diag_eigenvalues.

        Params:
        path_to_diag_eigenvalues - path to the file with diagonal eigenvalues
        """

        eigenvals_raw = np.loadtxt(path_to_diag_eigenvalues)
        eigvals_re = eigenvals_raw[:, 0]  # real part
        eigvals_im = eigenvals_raw[:, 1]  # imaginary part
        self.__diag_eigenvalues = eigvals_re + 1j * eigvals_im

    def __load_diag_matrix_elements(self, path_to_diag_matrix_elements):
        """
        Loads diagonal matrix elements and saves them to self.__diag_matrix_elements.

        Params:
        path_to_diag_matrix_elements - path to the file with diagonal eigenvalues
        """

        matrix_elements_raw = np.loadtxt(path_to_diag_matrix_elements)
        matrix_elements_raw = matrix_elements_raw[
            :, -2:
        ]  # take only the right eigenvector

        matrix_elements_re = matrix_elements_raw[:, 0]  # real part
        matrix_elements_im = matrix_elements_raw[:, 1]  # imaginary part

        self.__diag_matrix_elements = matrix_elements_re + 1j * matrix_elements_im

    def assert_diag_data_load(self):
        """
        Assertion that the diagonal data was loaded.
        """
        assert (
            self.__diag_loaded
        ), f"Diagonal matrix elements and eigenvalues are not loaded for {self.atom_name}!"

    def get_diag_matrix_elements(self):
        """
        Retruns:
        loaded diagonal matrix elements
        """

        self.assert_diag_data_load()

        return self.__diag_matrix_elements

    def get_diag_eigenvalues(self):
        """
        Retruns:
        loaded diagonal eigenvalues
        """

        self.assert_diag_data_load()

        return self.__diag_eigenvalues

    def load_hole(
        self,
        n_qn,
        hole_kappa,
        path_to_data,
        path_to_omega=None,
        path_to_pcur_all=None,
        path_to_amp_all=None,
        path_to_phaseF_all=None,
        path_to_phaseG_all=None,
        binding_energy=None,
        path_to_hf_energies=None,
        path_to_sp_ekin=None,
        should_reload=False,
    ):
        """
        Initializes hole, corresponding ionization paths and loads data for them.

        Params:
        n_qn - principal quantum number of the hole
        hole_kappa - kappa value of the hole
        path_to_data - path to the output folder with Fortran simulation results
        path_to_omega - path to the omega.dat file with XUV photon energies for the given hole
        (usually in pert folders). If not specified, constructed for path_to_data
        path_to_pcur_all - path to file with probabilty current for one photon.
        If not specified, constructed for path_to_data
        path_to_amp_all - path to file with amplitudes for one photon.
        If not specified, constructed for path_to_data
        path_to_phaseF_all - path to file with the phase for larger relativistic component
        of the wave function. If not specified, constructed for path_to_data
        path_to_phaseG_all - path to file with the phase for smaller relativistic component
        of the wave function. If not specified, constructed for path_to_data
        binding_energy - binding energy for the hole. Allows you to specify the predifined
        value for the hole's binding energy instead of loading it from the simulation data.
        path_to_hf_energies - path to the file with Hartree Fock energies for the given hole.
        If not specified, constructed for path_to_data
        path_to_sp_ekin - path to the file with kinetic energies for the given hole from
        secondphoton folder. If not specified, constructed for path_to_data
        should_reload - tells whether we should reload if the hole was previously
        loaded
        """

        is_loaded = self.is_hole_loaded(hole_kappa, n_qn)

        if not is_loaded or should_reload:
            hole = Hole(
                self.atom_name, hole_kappa, n_qn, binding_energy=binding_energy
            )  # initialize hole object

            if is_loaded and should_reload:
                print(f"Reload {hole.name} hole!")

            # If the paths to the pcur, amplitude, phase and omega files were not specified
            # we assume that they are in the pert folder.
            pert_path = (
                path_to_data + f"pert_{hole.kappa}_{hole.n - hole.l}" + os.path.sep
            )

            if path_to_pcur_all is None:
                path_to_pcur_all = pert_path + "pcur_all.dat"
            if path_to_amp_all is None:
                path_to_amp_all = pert_path + "amp_all.dat"
            if path_to_phaseF_all is None:
                path_to_phaseF_all = pert_path + "phaseF_all.dat"
            if path_to_phaseG_all is None:
                path_to_phaseG_all = pert_path + "phaseG_all.dat"
            if path_to_omega is None:
                path_to_omega = pert_path + "omega.dat"

            if (
                not binding_energy
            ):  # if the value for binding energy hasn't been provided - load it from data

                # if paths to the HF and kinetic energies are not specified, we assume
                # that they are in the seconphoton folder
                if path_to_hf_energies is None:
                    path_to_hf_energies = (
                        path_to_data
                        + "hf_wavefunctions"
                        + os.path.sep
                        + f"hf_energies_kappa_{hole.kappa}.dat"
                    )

                if path_to_sp_ekin is None:
                    path_to_sp_ekin = (
                        path_to_data
                        + "second_photon"
                        + os.path.sep
                        + f"energy_rpa_{hole.kappa}_{hole.n - hole.l}.dat"
                    )

                hole._load_binding_energy(
                    path_to_hf_energies,
                    path_to_omega=path_to_omega,
                    path_to_sp_ekin=path_to_sp_ekin,
                )

            # load data for ionization channels
            self.__channels[(n_qn, hole_kappa)] = Channels(
                path_to_omega,
                path_to_pcur_all,
                path_to_amp_all,
                path_to_phaseF_all,
                path_to_phaseG_all,
                hole,
            )
            self.num_channels += 1

    def is_hole_loaded(self, n_qn, hole_kappa):
        """
        Checks if the hole is loaded (contained in self.__channels)

        Params:
        n_qn - principal quantum number of the hole
        hole_kappa - kappa value of the hole

        Returns:
        True if loaded, False otherwise.
        """

        return (n_qn, hole_kappa) in self.__channels

    def assert_hole_load(self, n_qn, hole_kappa):
        """
        Assertion that the hole was loaded.

        Params:
        hole - object of the Hole class containing hole's parameters
        n_qn - principal quantum number of the hole
        hole_kappa - kappa value of the hole
        """

        assert self.is_hole_loaded(
            n_qn, hole_kappa
        ), f"The {construct_hole_name(self.atom_name, n_qn, hole_kappa)} hole is not loaded!"

    def get_channels_for_hole(self, n_qn, hole_kappa):
        """
        Returns ionization channels from self.__channels for the given hole.

        Params:
        n_qn - principal quantum number of the hole
        hole_kappa - kappa value of the hole

        Returns:
        channels - channels for the given hole
        """

        self.assert_hole_load(n_qn, hole_kappa)

        channels = self.__channels[(n_qn, hole_kappa)]

        return channels

    def get_all_channels(self):
        """
        Returns loaded channels for all holes (self.__channels)
        """

        return self.__channels

    def get_channel_labels_for_hole(self, n_qn, hole_kappa):
        """
        Constructs labels for all ionization channels of the given hole.

        Params:
        n_qn - principal quantum number of the hole
        hole_kappa - kappa value of the hole

        Returns:
        channel_labels - list with labels of all ionization channels
        """

        self.assert_hole_load(n_qn, hole_kappa)

        channel_labels = []
        channels = self.get_channels_for_hole(n_qn, hole_kappa)
        hole = channels.get_hole_object()
        hole_name = hole.name
        ionisation_paths = channels.get_all_ionisation_paths()
        for final_kappa in ionisation_paths.keys():
            ionisation_path = channels.get_ionisation_path(final_kappa)
            channel_labels.append(hole_name + " to " + ionisation_path.name)

        return channel_labels
