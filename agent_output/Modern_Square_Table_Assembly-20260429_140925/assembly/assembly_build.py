# -*- coding: utf-8 -*-
from pysw import SldWorksApp, AssemDoc
import os

def main():
    # 1. Initialize Application and Assembly Document
    sw_app = SldWorksApp()
    assem_name = "Modern_Square_Table_Assembly"
    
    # Define paths based on workspace configuration
    base_dir = r"D:\a_src\python\sw_agent\agent_output\Modern_Square_Table_Assembly-20260429_140925"
    parts_dir = os.path.join(base_dir, "parts")
    assembly_dir = os.path.join(base_dir, "assembly")
    
    # Ensure assembly directory exists
    if not os.path.exists(assembly_dir):
        os.makedirs(assembly_dir)

    print(f"[LOG] Creating assembly document: {assem_name}")
    sw_assem = AssemDoc(sw_app.createAndActivate_sw_assembly(assem_name))
    
    # 2. Define Part File Paths (Part ID -> Model File)
    part_files = {
        "table_top": os.path.join(parts_dir, "table_top", "table_top.SLDPRT"),
        "table_leg": os.path.join(parts_dir, "table_leg", "table_leg.SLDPRT"),
        "cross_beam_frame": os.path.join(parts_dir, "cross_beam_frame", "cross_beam_frame.SLDPRT")
    }

    # Verify files exist
    for pid, fpath in part_files.items():
        if not os.path.exists(fpath):
            print(f"[ERROR] Part file missing for {pid}: {fpath}")
            return

    # 3. Insert Components and Map Instance ID -> Component Name
    instance_map = {}
    
    # --- Insert Table Top (Base) ---
    print("[LOG] Inserting Table Top...")
    comp_table_top = sw_assem.add_component(part_files["table_top"], 0, 0, 0)
    if comp_table_top:
        instance_map["inst_table_top_1"] = comp_table_top
        print(f"[LOG] Table Top inserted as: {comp_table_top}")
    else:
        print("[ERROR] Failed to insert Table Top")
        return

    # --- Insert Legs (Repeated Part) ---
    # Positions are relative to table center. 
    # Table is 1200x600. Legs are at corners.
    # Assuming leg cross section 40x40.
    # FL: X=-580, Y=-280 (approx corner offset)
    # FR: X=580, Y=-280
    # BL: X=-580, Y=280
    # BR: X=580, Y=280
    # Note: add_component places the component origin. We place them roughly near their final position to help solver.
    
    leg_positions = {
        "inst_leg_fl": (-0.58, -0.28, -0.72), # Z approx bottom of leg
        "inst_leg_fr": (0.58, -0.28, -0.72),
        "inst_leg_bl": (-0.58, 0.28, -0.72),
        "inst_leg_br": (0.58, 0.28, -0.72)
    }

    for inst_id, pos in leg_positions.items():
        print(f"[LOG] Inserting Leg instance: {inst_id}...")
        comp_leg = sw_assem.add_component(part_files["table_leg"], pos[0], pos[1], pos[2])
        if comp_leg:
            instance_map[inst_id] = comp_leg
            print(f"[LOG] {inst_id} inserted as: {comp_leg}")
        else:
            print(f"[ERROR] Failed to insert {inst_id}")
            return

    # --- Insert Cross Beam Frame ---
    print("[LOG] Inserting Cross Beam Frame...")
    # Positioned at Z = -0.62m (100mm from ground, ground is -0.72m)
    comp_beam = sw_assem.add_component(part_files["cross_beam_frame"], 0, 0, -0.62)
    if comp_beam:
        instance_map["inst_cross_beam_1"] = comp_beam
        print(f"[LOG] Cross Beam inserted as: {comp_beam}")
    else:
        print("[ERROR] Failed to insert Cross Beam")
        return

    # 4. Apply Constraints
    
    # Helper to get component name safely
    def get_comp(inst_id):
        return instance_map.get(inst_id)

    # --- Fix Table Top ---
    # The first component added is usually fixed by default in SW, but we ensure it conceptually.
    # No explicit API call needed for 'fix' if it's the first component, but we log it.
    print("[LOG] Constraint: Fix Table Top (Base)")

    # --- Mate Legs to Table Top ---
    # Relation: face_coincident, alignment: opposed
    # Source: Leg top_face, Target: Table bottom_face
    
    legs_to_mate = ["inst_leg_fl", "inst_leg_fr", "inst_leg_bl", "inst_leg_br"]
    
    for leg_inst in legs_to_mate:
        c_leg = get_comp(leg_inst)
        c_top = get_comp("inst_table_top_1")
        
        if c_leg and c_top:
            print(f"[LOG] Mating {leg_inst} top_face to Table Top bottom_face...")
            try:
                sw_assem.mate_faces(assem_name, c_leg, c_top, "top_face", "bottom_face", aligned=False)
                print(f"[LOG] Success: Face mate for {leg_inst}")
            except Exception as e:
                print(f"[WARN] Face mate failed for {leg_inst}: {e}")
        else:
            print(f"[ERROR] Missing components for mating {leg_inst}")

    # --- Mate Cross Beam to Legs ---
    # The beam connects inner faces of the legs.
    # 1. Beam end_face_x_minus <-> Leg FL inner_face_x_plus
    # 2. Beam end_face_x_plus <-> Leg FR inner_face_x_minus
    # 3. Beam end_face_y_minus <-> Leg FL inner_face_y_plus
    # 4. Beam end_face_y_plus <-> Leg BL inner_face_y_minus
    
    c_beam = get_comp("inst_cross_beam_1")
    c_leg_fl = get_comp("inst_leg_fl")
    c_leg_fr = get_comp("inst_leg_fr")
    c_leg_bl = get_comp("inst_leg_bl")
    
    if c_beam and c_leg_fl and c_leg_fr and c_leg_bl:
        
        # Mate 1: Beam Left to FL Leg Inner X+
        print("[LOG] Mating Beam end_face_x_minus to FL Leg inner_face_x_plus...")
        try:
            sw_assem.mate_faces(assem_name, c_beam, c_leg_fl, "end_face_x_minus", "inner_face_x_plus", aligned=False)
            print("[LOG] Success: Beam-FL X mate")
        except Exception as e:
            print(f"[WARN] Beam-FL X mate failed: {e}")

        # Mate 2: Beam Right to FR Leg Inner X-
        print("[LOG] Mating Beam end_face_x_plus to FR Leg inner_face_x_minus...")
        try:
            sw_assem.mate_faces(assem_name, c_beam, c_leg_fr, "end_face_x_plus", "inner_face_x_minus", aligned=False)
            print("[LOG] Success: Beam-FR X mate")
        except Exception as e:
            print(f"[WARN] Beam-FR X mate failed: {e}")

        # Mate 3: Beam Front to FL Leg Inner Y+
        print("[LOG] Mating Beam end_face_y_minus to FL Leg inner_face_y_plus...")
        try:
            sw_assem.mate_faces(assem_name, c_beam, c_leg_fl, "end_face_y_minus", "inner_face_y_plus", aligned=False)
            print("[LOG] Success: Beam-FL Y mate")
        except Exception as e:
            print(f"[WARN] Beam-FL Y mate failed: {e}")

        # Mate 4: Beam Back to BL Leg Inner Y-
        print("[LOG] Mating Beam end_face_y_plus to BL Leg inner_face_y_minus...")
        try:
            sw_assem.mate_faces(assem_name, c_beam, c_leg_bl, "end_face_y_plus", "inner_face_y_minus", aligned=False)
            print("[LOG] Success: Beam-BL Y mate")
        except Exception as e:
            print(f"[WARN] Beam-BL Y mate failed: {e}")
            
    else:
        print("[ERROR] Missing components for Beam-Leg mating")

    # 5. Save Assembly
    output_path = os.path.join(assembly_dir, "Modern_Square_Table_Assembly.SLDASM")
    print(f"[LOG] Saving assembly to: {output_path}")
    try:
        sw_assem.save_as(output_path)
        print("[LOG] Assembly saved successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to save assembly: {e}")

if __name__ == "__main__":
    main()