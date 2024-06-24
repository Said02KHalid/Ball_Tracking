from collections import deque
from imutils.video import VideoStream
import numpy as np
import argparse
import cv2
import imutils
import time
import matplotlib.pyplot as plt

def main():
    # Configuration des arguments de la ligne de commande
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video", help="path to the (optional) video file")
    ap.add_argument("-b", "--buffer", type=int, default=64, help="max buffer size")
    ap.add_argument("-o", "--output", help="path to the output video file")
    args = vars(ap.parse_args())

    # Définition des bornes pour la couleur verte en HSV
    greenLower = (29, 86, 6)
    greenUpper = (64, 255, 255)

    # Initialisation de la deque pour stocker les points suivis
    pts = deque(maxlen=args["buffer"])
    path = []  # Liste pour stocker les coordonnées

    # Initialisation du flux vidéo
    if not args.get("video", False):
        print("[INFO] starting video stream...")
        vs = VideoStream(src=0).start()
        time.sleep(2.0)
    else:
        print("[INFO] opening video file...")
        vs = cv2.VideoCapture(args["video"])

    if args.get("video", False) and not vs.isOpened():
        print("[ERROR] Cannot open video file.")
        return

    writer = None  # Initialisation du writer

    try:
        # Boucle principale
        while True:
            frame = vs.read()
            frame = frame[1] if args.get("video", False) else frame

            # Si nous visualisons une vidéo et que nous n'avons pas obtenu de frame, nous avons atteint la fin de la vidéo
            if frame is None:
                print("[INFO] no frame received, ending loop...")
                break

            # Redimensionnement de la frame, application d'un flou et conversion en espace de couleurs HSV
            frame = imutils.resize(frame, width=600)
            blurred = cv2.GaussianBlur(frame, (11, 11), 0)
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

            # Construction d'un masque pour la couleur verte, puis application d'érosions et dilatations pour éliminer les petits blobs
            mask = cv2.inRange(hsv, greenLower, greenUpper)
            mask = cv2.erode(mask, None, iterations=2)
            mask = cv2.dilate(mask, None, iterations=2)

            # Recherche des contours dans le masque et initialisation du centre (x, y) de la balle
            cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)
            center = None

            # Si au moins un contour a été trouvé
            if len(cnts) > 0:
                # Trouver le plus grand contour dans le masque, puis utiliser pour calculer le cercle englobant minimum et le centroïde
                c = max(cnts, key=cv2.contourArea)
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                M = cv2.moments(c)
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                # Si le rayon répond à une taille minimale
                if radius > 10:
                    # Dessiner le cercle et le centroïde sur la frame, puis mettre à jour la liste des points suivis
                    cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                    cv2.circle(frame, center, 5, (0, 0, 255), -1)
                    path.append(center)  # Enregistrer les coordonnées

            # Mise à jour de la queue des points
            pts.appendleft(center)

            # Boucle sur l'ensemble des points suivis
            for i in range(1, len(pts)):
                # Ignorer les points suivis s'ils sont None
                if pts[i - 1] is None or pts[i] is None:
                    continue

                # Calculer l'épaisseur de la ligne et dessiner les lignes de connexion
                thickness = int(np.sqrt(args["buffer"] / float(i + 1)) * 2.5)
                cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

            # Initialiser le writer vidéo si nécessaire
            if writer is None and args.get("output", False):
                fourcc = cv2.VideoWriter_fourcc(*"MJPG")
                writer = cv2.VideoWriter(args["output"], fourcc, 30, (frame.shape[1], frame.shape[0]), True)

            # Écrire la frame dans le fichier de sortie
            if writer is not None:
                writer.write(frame)

            # Afficher la frame à l'écran
            cv2.imshow("Frame", frame)
            key = cv2.waitKey(1) & 0xFF

            # Si la touche 'q' est pressée, quitter la boucle
            if key == ord("q"):
                print("[INFO] 'q' key pressed, exiting loop...")
                break
    except KeyboardInterrupt:
        print("[INFO] KeyboardInterrupt caught, exiting loop...")
    finally:
        # Si nous n'utilisons pas un fichier vidéo, arrêter le flux vidéo de la caméra
        if not args.get("video", False):
            print("[INFO] stopping video stream...")
            vs.stop()
        # Sinon, libérer la caméra
        else:
            print("[INFO] releasing video capture...")
            vs.release()

        # Relâcher le writer vidéo
        if writer is not None:
            print("[INFO] releasing video writer...")
            writer.release()

        # Fermer toutes les fenêtres
        print("[INFO] destroying all windows...")
        cv2.destroyAllWindows()

        # Tracer le chemin de la balle
        if path:
            x_coords, y_coords = zip(*path)
            plt.plot(x_coords, y_coords, marker='o')
            plt.title('Path of the Ball')
            plt.xlabel('X')
            plt.ylabel('Y')
            plt.gca().invert_yaxis()  # Inverser l'axe Y pour correspondre à la vue de la caméra
            plt.show()

if __name__ == "__main__":
    main()
