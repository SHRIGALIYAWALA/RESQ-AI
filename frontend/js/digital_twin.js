class BuildingDigitalTwin {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
    this.currentFloor = 1;
    this.buildingData = null;
    this.dangerZones = [];
    this.evacuationRoutes = [];
    this.animOffset = 0;

    if (this.canvas) {
      this._resizeCanvas();
      window.addEventListener("resize", () => this._resizeCanvas());
      this._startAnimation();
    }
  }

  _resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height || 420;
    this.render();
  }

  updateData(buildingData, dangerZones = [], evacuationRoutes = []) {
    this.buildingData = buildingData;
    this.dangerZones = dangerZones;
    this.evacuationRoutes = evacuationRoutes;
    this.render();
  }

  setFloor(floorNum) {
    this.currentFloor = parseInt(floorNum);
    this.render();
  }

  _startAnimation() {
    const loop = () => {
      this.animOffset = (this.animOffset + 0.5) % 20;
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  render() {
    if (!this.ctx || !this.canvas) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Clear background
    ctx.fillStyle = "#090c14";
    ctx.fillRect(0, 0, w, h);

    // Draw floor grid pattern
    ctx.strokeStyle = "rgba(0, 243, 255, 0.05)";
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 30) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Default 2-floor layout representation if no external geo coordinates
    const layout = [
      { name: "Room 101", x: 40, y: 50, width: 140, height: 100, floor: 1, capacity: 20, occ: 4 },
      { name: "Room 102", x: 220, y: 50, width: 140, height: 100, floor: 1, capacity: 25, occ: 8 },
      { name: "Central Corridor", x: 40, y: 170, width: 440, height: 60, floor: 1, isCorridor: true },
      { name: "Room 103", x: 40, y: 250, width: 140, height: 100, floor: 1, capacity: 15, occ: 2 },
      { name: "Emergency Exit A", x: 500, y: 170, width: 90, height: 60, floor: 1, isExit: true },
      { name: "Emergency Exit B", x: 40, y: 370, width: 120, height: 40, floor: 1, isExit: true },

      { name: "Room 201", x: 40, y: 50, width: 140, height: 100, floor: 2, capacity: 20, occ: 3 },
      { name: "Room 202", x: 220, y: 50, width: 140, height: 100, floor: 2, capacity: 25, occ: 12 },
      { name: "Corridor Floor 2", x: 40, y: 170, width: 440, height: 60, floor: 2, isCorridor: true },
      { name: "Room 203", x: 40, y: 250, width: 140, height: 100, floor: 2, capacity: 15, occ: 0 },
      { name: "Stairwell North", x: 500, y: 170, width: 90, height: 60, floor: 2, isExit: true },
    ];

    const currentRooms = layout.filter((r) => r.floor === this.currentFloor);

    // Draw rooms and zones
    currentRooms.forEach((room) => {
      // Determine danger level
      let riskScore = 0.05;
      const dz = this.dangerZones.find((z) => z.name === room.name || (z.location && z.location.includes(room.name)));
      if (dz) {
        riskScore = dz.risk_score || 0.85;
      }

      let strokeColor = "rgba(0, 243, 255, 0.4)";
      let fillColor = "rgba(16, 23, 38, 0.7)";

      if (room.isExit) {
        strokeColor = "#00ff88";
        fillColor = "rgba(0, 255, 136, 0.15)";
      } else if (riskScore >= 0.8) {
        strokeColor = "#ff0055";
        fillColor = "rgba(255, 0, 85, 0.25)";
      } else if (riskScore >= 0.5) {
        strokeColor = "#ffb700";
        fillColor = "rgba(255, 183, 0, 0.2)";
      }

      // Draw box
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2;
      ctx.fillStyle = fillColor;
      ctx.fillRect(room.x, room.y, room.width, room.height);
      ctx.strokeRect(room.x, room.y, room.width, room.height);

      // Label
      ctx.fillStyle = room.isExit ? "#00ff88" : "#ffffff";
      ctx.font = "bold 12px sans-serif";
      ctx.fillText(room.name, room.x + 8, room.y + 20);

      // Occupants / Capacity badge
      if (!room.isExit && !room.isCorridor) {
        ctx.fillStyle = "rgba(0, 243, 255, 0.8)";
        ctx.font = "11px monospace";
        ctx.fillText(`👥 ${room.occ || 0}/${room.capacity || 20}`, room.x + 8, room.y + 40);

        if (riskScore >= 0.8) {
          ctx.fillStyle = "#ff0055";
          ctx.font = "bold 11px sans-serif";
          ctx.fillText("🔥 DANGER", room.x + 8, room.y + 65);
        }
      }
    });

    // Draw animated evacuation paths
    this.evacuationRoutes.forEach((route) => {
      const pathNodes = route.path || [];
      if (pathNodes.length < 2) return;

      ctx.save();
      ctx.strokeStyle = "#00f3ff";
      ctx.lineWidth = 3;
      ctx.setLineDash([8, 6]);
      ctx.lineDashOffset = -this.animOffset;

      ctx.beginPath();
      for (let i = 0; i < pathNodes.length; i++) {
        const roomMeta = currentRooms.find((r) => r.name === pathNodes[i]);
        if (roomMeta) {
          const cx = roomMeta.x + roomMeta.width / 2;
          const cy = roomMeta.y + roomMeta.height / 2;
          if (i === 0) ctx.moveTo(cx, cy);
          else ctx.lineTo(cx, cy);
        }
      }
      ctx.stroke();
      ctx.restore();
    });

    // Draw Floor Banner
    ctx.fillStyle = "#00f3ff";
    ctx.font = "bold 13px monospace";
    ctx.fillText(`FLOOR ${this.currentFloor} - DIGITAL TWIN VIEW`, 20, 25);
  }
}

window.BuildingDigitalTwin = BuildingDigitalTwin;
